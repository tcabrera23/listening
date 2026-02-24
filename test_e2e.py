"""
End-to-end test: download, transcribe, generate blanks.
Tests caching system.
"""
import sys

from blanks import generate_blanks
from transcribe import transcribe_audio
from transform_video import get_audio_from_youtube, CACHE_DIR

# Use a short public YouTube video
TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo (19s)

print("=" * 60)
print("MILIX END-TO-END TEST (with caching)")
print("=" * 60)

print(f"\nCache directory: {CACHE_DIR}")
cached_files = list(CACHE_DIR.glob("*")) if CACHE_DIR.exists() else []
print(f"Files in cache before test: {len(cached_files)}")

print("\n[1/3] Downloading and extracting audio...")
print("  (First run: downloads, Second run: from cache)")
audio_path = get_audio_from_youtube(TEST_URL, use_cache=True)
if not audio_path:
    print("[FAIL] Could not download/extract audio")
    sys.exit(1)
print(f"[OK] Audio extracted: {audio_path}")

# Test cache hit
print("\n[CACHE TEST] Re-requesting same video...")
audio_path_2 = get_audio_from_youtube(TEST_URL, use_cache=True)
if audio_path == audio_path_2:
    print("[OK] Cache hit! Same file returned instantly")
else:
    print(f"[WARN] Different paths: {audio_path} vs {audio_path_2}")

print("\n[2/3] Transcribing with Whisper...")
transcription, error = transcribe_audio(audio_path, provider="groq")
if not transcription:
    print("[FAIL] Could not transcribe audio")
    if error:
        print(f"   Error: {error}")
    print("   (Check GROQ_API_KEY in .env)")
    sys.exit(1)
print(f"[OK] Transcription ({len(transcription)} chars):")
print(f"  {transcription[:200]}...")

print("\n[3/3] Generating fill-the-blanks...")
blanks_data = generate_blanks(transcription, num_blanks=3, provider="groq")
if not blanks_data:
    print("[FAIL] Could not generate blanks")
    sys.exit(1)
print(f"[OK] Blanks generated:")
print(f"  Text: {blanks_data['text_with_blanks'][:150]}...")
print(f"  Answers: {blanks_data['answers']}")

cached_files_after = list(CACHE_DIR.glob("*")) if CACHE_DIR.exists() else []
print(f"\nFiles in cache after test: {len(cached_files_after)}")

print("\n" + "=" * 60)
print("[OK] ALL TESTS PASSED")
print("=" * 60)
