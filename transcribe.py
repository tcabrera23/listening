"""
Transcribe audio using Groq Whisper API (whisper-large-v3-turbo).
Falls back to OpenRouter if Groq fails.
Handles large files by splitting them into chunks.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_WHISPER = "whisper-large-v3-turbo"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Groq Whisper limits: 25MB (free tier)
# OpenAI Whisper limits: 25MB
MAX_FILE_SIZE_MB = 20


def _transcribe_single_file_openai(audio_path: str) -> tuple[str | None, str | None]:
    """Transcribe a single audio file with OpenAI Whisper. Returns (text, error_msg)."""
    if not OPENAI_API_KEY:
        return None, "OPENAI_API_KEY no configurada"
    
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return None, f"Archivo demasiado grande ({file_size_mb:.1f}MB). Máximo {MAX_FILE_SIZE_MB}MB"
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return (response.text if response else None), None
    except Exception as e:
        error_msg = str(e)
        if "413" in error_msg or "too large" in error_msg.lower():
            return None, f"Error 413: Archivo demasiado grande para OpenAI (límite ~25MB)"
        return None, f"Error OpenAI: {error_msg[:200]}"


def _transcribe_single_file_groq(audio_path: str) -> tuple[str | None, str | None]:
    """Transcribe a single audio file with Groq. Returns (text, error_msg)."""
    if not GROQ_API_KEY:
        return None, "GROQ_API_KEY no configurada"
    
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return None, f"Archivo demasiado grande ({file_size_mb:.1f}MB). Máximo {MAX_FILE_SIZE_MB}MB"
    
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=GROQ_MODEL_WHISPER,
                file=f,
            )
        return (response.text if response else None), None
    except Exception as e:
        error_msg = str(e)
        if "413" in error_msg or "too large" in error_msg.lower():
            return None, f"Error 413: Archivo demasiado grande para Groq (límite ~25MB)"
        return None, f"Error Groq: {error_msg[:200]}"


def _transcribe_with_chunks(audio_path: str, provider: str = "groq") -> tuple[list[str], str | None]:
    """
    Transcribe large audio by splitting into 5-minute chunks.
    Returns (list_of_transcriptions, error_msg).
    """
    from audio_splitter import split_audio_into_chunks, get_chunk_info
    
    info = get_chunk_info(audio_path, chunk_duration_minutes=5)
    if info["num_chunks"] == 0:
        return [], "No se pudo obtener información del audio"
    
    if info["num_chunks"] == 1:
        if provider == "openai":
            text, error = _transcribe_single_file_openai(audio_path)
        else:
            text, error = _transcribe_single_file_groq(audio_path)
        return ([text] if text else [], error)
    
    chunks = split_audio_into_chunks(audio_path, chunk_duration_minutes=5)
    if not chunks:
        return [], "No se pudieron crear los segmentos de audio"
    
    transcriptions = []
    for i, chunk_path in enumerate(chunks, 1):
        if provider == "openai":
            text, error = _transcribe_single_file_openai(chunk_path)
        else:
            text, error = _transcribe_single_file_groq(chunk_path)
        
        if not text:
            return [], f"Error en segmento {i}/{len(chunks)}: {error}"
        transcriptions.append(text)
    
    return transcriptions, None


def transcribe_audio(audio_path: str, provider: str = "groq") -> tuple[str | None, str | None]:
    """
    Transcribe an audio file. Automatically splits large files into chunks.
    
    Args:
        audio_path: Path to audio file
        provider: "groq", "openai", or "auto"
    
    Returns:
        (transcription_text, error_message)
    """
    path = Path(audio_path)
    if not path.is_file():
        return None, f"Archivo no encontrado: {audio_path}"
    
    if provider not in ["groq", "openai", "auto"]:
        return None, f"Proveedor no soportado: {provider}"
    
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    
    # Try direct transcription for small files
    if file_size_mb <= MAX_FILE_SIZE_MB:
        if provider == "groq":
            return _transcribe_single_file_groq(audio_path)
        elif provider == "openai":
            return _transcribe_single_file_openai(audio_path)
        else:  # auto
            text, err = _transcribe_single_file_groq(audio_path)
            if text:
                return text, None
            text_oa, err_oa = _transcribe_single_file_openai(audio_path)
            if text_oa:
                return text_oa, None
            return None, f"Groq: {err}, OpenAI: {err_oa}"
    
    # Large file: use chunking
    if provider == "auto":
        transcriptions, error = _transcribe_with_chunks(audio_path, "groq")
        if not error:
            combined = "\n\n".join(transcriptions)
            return combined, None
        transcriptions, error = _transcribe_with_chunks(audio_path, "openai")
        if not error:
            combined = "\n\n".join(transcriptions)
            return combined, None
        return None, error
    
    transcriptions, error = _transcribe_with_chunks(audio_path, provider)
    if error:
        return None, error
    
    combined = "\n\n".join(transcriptions)
    return combined, None


def transcribe_audio_by_segments(audio_path: str, provider: str = "groq") -> tuple[list[str] | None, str | None]:
    """
    Transcribe audio and return list of transcriptions per segment (for multi-tab display).
    
    Args:
        audio_path: Path to audio file
        provider: "groq", "openai", or "auto"
    
    Returns:
        (list_of_segment_transcriptions, error_message)
    """
    path = Path(audio_path)
    if not path.is_file():
        return None, f"Archivo no encontrado: {audio_path}"
    
    if provider not in ["groq", "openai", "auto"]:
        return None, f"Proveedor no soportado: {provider}"
    
    from audio_splitter import get_chunk_info
    
    info = get_chunk_info(audio_path, chunk_duration_minutes=5)
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    
    # Small file: single transcription
    if file_size_mb <= MAX_FILE_SIZE_MB and info["num_chunks"] <= 1:
        if provider == "groq":
            text, error = _transcribe_single_file_groq(audio_path)
        elif provider == "openai":
            text, error = _transcribe_single_file_openai(audio_path)
        else:  # auto
            text, err = _transcribe_single_file_groq(audio_path)
            if not text:
                text, err = _transcribe_single_file_openai(audio_path)
                error = err
            else:
                error = None
        return ([text] if text else None, error)
    
    # Large file: transcribe by chunks
    if provider == "auto":
        transcriptions, error = _transcribe_with_chunks(audio_path, "groq")
        if error:
            transcriptions, error = _transcribe_with_chunks(audio_path, "openai")
        return (transcriptions if transcriptions else None, error)
    
    return _transcribe_with_chunks(audio_path, provider)
