"""
Generate C1/C2 fill-in-the-blanks exercises from transcription.
Supports provider fallback and per-sentence blank density control.
"""
import json
import os
import random
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_MODEL_LLM = os.getenv("GROQ_MODEL_LLM", "llama-3.3-70b-versatile")
OPENROUTER_MODEL_LLM = os.getenv("OPENROUTER_MODEL_LLM", "google/gemini-2.0-flash-exp:free")
OPENAI_MODEL_LLM = os.getenv("OPENAI_MODEL_LLM", "gpt-4o-mini")

SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'-]+\b")

# Common particles for phrasal verbs (C2 heuristic)
PARTICLES = {
    "up", "down", "out", "off", "on", "in", "over", "through", 
    "away", "back", "around", "about", "along", "by", "for"
}

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "they", "them", "your", "you",
    "just", "what", "when", "were", "been", "about", "into", "than", "then", "very",
    "over", "also", "only", "much", "some", "more", "most", "their", "there", "would",
    "could", "should", "while", "where", "which", "whose", "because", "through", "after",
    "is", "are", "was", "will", "can", "not", "but", "for", "to", "in", "on", "at", "by"
}


def count_blanks_in_text(text: str) -> int:
    return len(re.findall(r"__+", text))


def _max_blanks_per_sentence_ok(text: str, max_blanks_per_sentence: int) -> bool:
    for sentence in SENTENCE_RE.findall(text):
        if count_blanks_in_text(sentence) > max_blanks_per_sentence:
            return False
    return True


def _is_valid_result(
    result: dict[str, Any] | None,
    num_blanks: int,
    max_blanks_per_sentence: int,
) -> bool:
    if not result:
        return False
    text = str(result.get("text_with_blanks", ""))
    answers = result.get("answers", [])
    if not isinstance(answers, list):
        return False
    if len(answers) != num_blanks:
        return False
    if count_blanks_in_text(text) != num_blanks:
        return False
    return _max_blanks_per_sentence_ok(text, max_blanks_per_sentence)


def _sentence_candidates(transcription: str, difficulty: str) -> list[list[tuple[int, int, str]]]:
    """
    Identifies candidate words/phrases for blanks in each sentence.
    For C2, tries to find phrasal verbs (word + particle).
    """
    min_len = 5 if difficulty == "C1" else 4
    sentence_candidates: list[list[tuple[int, int, str]]] = []

    for sentence_match in SENTENCE_RE.finditer(transcription):
        sentence = sentence_match.group(0)
        sentence_start = sentence_match.start()
        current_candidates: list[tuple[int, int, str]] = []
        
        words = list(WORD_RE.finditer(sentence))
        used_indices = set()

        # C2 Heuristic: Look for phrasal verbs (Verb + Particle)
        if difficulty == "C2":
            for i in range(len(words) - 1):
                w1 = words[i]
                w2 = words[i+1]
                w1_text = w1.group(0)
                w2_text = w2.group(0)
                
                # Simple check: Word + Particle
                if len(w1_text) >= 3 and w2_text.lower() in PARTICLES:
                    # Found potential phrasal verb
                    phrase = f"{w1_text} {w2_text}"
                    current_candidates.append((
                        sentence_start + w1.start(),
                        sentence_start + w2.end(),
                        phrase
                    ))
                    used_indices.add(i)
                    used_indices.add(i+1)

        # Standard word selection
        for i, w in enumerate(words):
            if i in used_indices:
                continue
                
            word = w.group(0)
            low = word.lower()
            
            # Skip stopwords and short words (unless C2 relaxed length)
            if low in STOPWORDS:
                continue
            if len(low) < min_len:
                continue
                
            current_candidates.append((
                sentence_start + w.start(),
                sentence_start + w.end(),
                word
            ))

        sentence_candidates.append(current_candidates)

    return sentence_candidates


def _heuristic_generate_blanks(
    transcription: str,
    num_blanks: int,
    difficulty: str,
    max_blanks_per_sentence: int,
) -> dict[str, Any] | None:
    candidates_by_sentence = _sentence_candidates(transcription, difficulty)
    total_candidates = sum(len(x) for x in candidates_by_sentence)
    
    if total_candidates == 0:
        # Fallback if no candidates found with strict rules
        return None

    target = min(num_blanks, total_candidates)
    rng = random.SystemRandom()

    selected: list[tuple[int, int, str]] = []
    count_by_sentence = [0] * len(candidates_by_sentence)

    # 1. First pass: Select strictly respecting max_blanks_per_sentence
    while len(selected) < target:
        # Find sentences that can still accept blanks
        available_indices = [
            i for i, cands in enumerate(candidates_by_sentence)
            if cands and count_by_sentence[i] < max_blanks_per_sentence
        ]
        
        if not available_indices:
            break
            
        sidx = rng.choice(available_indices)
        
        # Pick a random candidate from this sentence
        pick = rng.choice(candidates_by_sentence[sidx])
        
        # Remove it from candidates to avoid double selection
        candidates_by_sentence[sidx].remove(pick)
        
        selected.append(pick)
        count_by_sentence[sidx] += 1

    # 2. Second pass (Relaxed): If we still need blanks, ignore max_blanks constraint
    # (Only if we couldn't satisfy with strict rules)
    while len(selected) < target:
        available_indices = [i for i, cands in enumerate(candidates_by_sentence) if cands]
        
        if not available_indices:
            break
            
        sidx = rng.choice(available_indices)
        pick = rng.choice(candidates_by_sentence[sidx])
        candidates_by_sentence[sidx].remove(pick)
        selected.append(pick)

    # Sort selected blanks by position in text (critical for correct reconstruction)
    selected.sort(key=lambda x: x[0])

    # Reconstruct text with blanks
    answers: list[str] = []
    chunks: list[str] = []
    last_idx = 0
    
    for start, end, text_segment in selected:
        chunks.append(transcription[last_idx:start])
        chunks.append("__")
        answers.append(text_segment)
        last_idx = end
        
    chunks.append(transcription[last_idx:])
    text_with_blanks = "".join(chunks)

    return {"text_with_blanks": text_with_blanks, "answers": answers}


def _build_prompt(
    transcription: str,
    num_blanks: int,
    difficulty: str,
    max_blanks_per_sentence: int,
) -> str:
    focus_instruction = (
        "Focus on academic vocabulary, complex verbs, and nouns." 
        if difficulty == "C1" else 
        "Focus heavily on PHRASAL VERBS (e.g., 'give up', 'turn into'), COLLOCATIONS, and IDIOMS."
    )

    return f"""You are an expert English teacher creating a {difficulty} level listening exercise.

Task: Replace exactly {num_blanks} items in the text with "__".

Rules:
1. **Target Level**: {difficulty}. {focus_instruction}
2. **Distribution**: Distribute blanks randomly across the ENTIRE text. Do NOT cluster them.
3. **Density**: Maximum {max_blanks_per_sentence} blanks per sentence.
4. **Items**: A "blank" can be a single word OR a short phrase (like a phrasal verb).
5. **Output**: Return ONLY valid JSON.

Input Text:
{transcription}

Output JSON Format:
{{
  "text_with_blanks": "The string with __ replacing the selected items.",
  "answers": ["list", "of", "removed", "items", "in", "order"]
}}
"""


def _parse_llm_response(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        # Strip code blocks
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict) or "text_with_blanks" not in data or "answers" not in data:
        return None

    answers = data["answers"]
    if not isinstance(answers, list):
        answers = [answers]
        
    return {
        "text_with_blanks": str(data["text_with_blanks"]),
        "answers": [str(a).strip() for a in answers],
    }


def _call_llm(prompt: str, provider: str) -> dict[str, Any] | None:
    api_key = None
    base_url = None
    model = None
    
    if provider == "groq":
        api_key = GROQ_API_KEY
        base_url = "https://api.groq.com/openai/v1"
        model = GROQ_MODEL_LLM
    elif provider == "openai":
        api_key = OPENAI_API_KEY
        model = OPENAI_MODEL_LLM
    elif provider == "openrouter":
        api_key = OPENROUTER_API_KEY
        base_url = "https://openrouter.ai/api/v1"
        model = OPENROUTER_MODEL_LLM
        
    if not api_key:
        return None
        
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4, # Slightly lower temp for adherence to rules
        )
        text = resp.choices[0].message.content if resp.choices else None
        return _parse_llm_response(text) if text else None
    except Exception as e:
        print(f"LLM Error ({provider}): {e}")
        return None


def generate_blanks(
    transcription: str,
    num_blanks: int = 5,
    provider: str = "groq",
    difficulty: str = "C1",
    max_blanks_per_sentence: int = 2,
) -> dict[str, Any] | None:
    """
    Main function to generate exercises.
    Tries selected provider -> auto fallback -> heuristic.
    """
    if not transcription or num_blanks < 1:
        return None

    # Normalize inputs
    difficulty = difficulty if difficulty in {"C1", "C2"} else "C1"
    max_blanks_per_sentence = max(1, min(3, max_blanks_per_sentence))
    
    prompt = _build_prompt(transcription, num_blanks, difficulty, max_blanks_per_sentence)
    result = None

    # Strategy: Provider -> Fallback Chain
    providers_to_try = []
    if provider in ["groq", "openai", "openrouter"]:
        providers_to_try.append(provider)
    
    # Auto fallbacks
    if provider == "auto" or True: # Always allow fallback if primary fails
        if "groq" not in providers_to_try: providers_to_try.append("groq")
        if "openai" not in providers_to_try: providers_to_try.append("openai")
        if "openrouter" not in providers_to_try: providers_to_try.append("openrouter")
    
    # Execute chain
    for p in providers_to_try:
        result = _call_llm(prompt, p)
        if _is_valid_result(result, num_blanks, max_blanks_per_sentence):
            break # Success
        result = None # Invalid result, try next

    # Final Fallback: Heuristic
    if not result:
        result = _heuristic_generate_blanks(
            transcription,
            num_blanks,
            difficulty,
            max_blanks_per_sentence,
        )
        
    return result
