import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from audio_splitter import split_audio_into_chunks, get_chunk_info

file_path = "files/Iz9HydQZhPo.m4a"
print(f"Testing split on file: {file_path}")

if os.path.exists(file_path):
    info = get_chunk_info(file_path, chunk_duration_minutes=5)
    print(f"Info: {info}")
    
    if info['num_chunks'] > 1:
        print("Splitting...")
        chunks = split_audio_into_chunks(file_path, chunk_duration_minutes=5)
        print(f"Chunks created: {len(chunks)}")
        for c in chunks:
            print(f" - {c} ({os.path.getsize(c) / (1024*1024):.2f} MB)")
    else:
        print("No split needed (or duration failed)")
else:
    print("File not found")
