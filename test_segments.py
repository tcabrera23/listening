"""
Quick test: Audio splitting and transcription by segments.
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("TEST: Audio Splitting and Segment Transcription")
print("=" * 60)

# Test 1: Download video and check chunking
print("\n[TEST 1] Downloading video...")
from transform_video import get_audio_from_youtube

url = "https://www.youtube.com/watch?v=Iz9HydQZhPo"
audio_path = get_audio_from_youtube(url, use_cache=True)

if not audio_path:
    print("[FAIL] Could not download audio")
    exit(1)

print(f"[OK] Audio downloaded: {audio_path}")

# Test 2: Check audio duration and chunks
print("\n[TEST 2] Checking audio duration and chunks...")
from audio_splitter import get_chunk_info

info = get_chunk_info(audio_path, chunk_duration_minutes=5)
duration_min = info["duration"] / 60
num_chunks = info["num_chunks"]

print(f"Duration: {duration_min:.1f} minutes")
print(f"Expected chunks (5 min each): {num_chunks}")

if num_chunks == 0:
    print("[FAIL] Could not get audio info")
    exit(1)

print(f"[OK] Audio will be split into {num_chunks} segments")

# Test 3: Transcribe by segments
print(f"\n[TEST 3] Transcribing {num_chunks} segments with Groq...")
if not os.getenv("GROQ_API_KEY"):
    print("[SKIP] GROQ_API_KEY not configured")
    exit(0)

from transcribe import transcribe_audio_by_segments

transcriptions, error = transcribe_audio_by_segments(audio_path, provider="groq")

if not transcriptions:
    print(f"[FAIL] Transcription failed: {error}")
    exit(1)

print(f"[OK] Transcribed {len(transcriptions)} segments")
for i, trans in enumerate(transcriptions, 1):
    print(f"  Segment {i}: {len(trans)} chars - {trans[:80]}...")

# Test 4: Generate blanks for each segment
print(f"\n[TEST 4] Generating blanks for {len(transcriptions)} segments...")
from blanks import generate_blanks

for i, trans in enumerate(transcriptions, 1):
    blanks_data = generate_blanks(trans, num_blanks=5, provider="groq")
    if blanks_data:
        print(f"[OK] Segment {i}: {len(blanks_data['answers'])} blanks generated")
    else:
        print(f"[WARN] Segment {i}: Could not generate blanks")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
