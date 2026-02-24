import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from audio_splitter import get_audio_duration

file_path = "files/Iz9HydQZhPo.m4a"
print(f"Testing file: {file_path}")
if os.path.exists(file_path):
    print(f"File exists. Size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
    duration = get_audio_duration(file_path)
    print(f"Duration: {duration}")
else:
    print("File does not exist")

try:
    import moviepy.editor as mp
    print("MoviePy imported via moviepy.editor")
except ImportError:
    print("MoviePy.editor import failed")

try:
    from moviepy import AudioFileClip
    print("MoviePy imported via moviepy (v2+)")
except ImportError:
    print("MoviePy direct import failed")
