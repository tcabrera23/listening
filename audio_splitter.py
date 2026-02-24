"""
Split audio files into chunks for large file transcription.
Uses imageio-ffmpeg binary (bundled with moviepy) for reliable splitting without system install.
"""
import os
import re
import subprocess
from pathlib import Path

try:
    import imageio_ffmpeg
    FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_BINARY = "ffmpeg"  # Fallback to system command


def get_audio_duration(audio_path: str) -> float | None:
    """Get duration of audio file in seconds. Tries MoviePy first, then ffmpeg parsing."""
    if not os.path.isfile(audio_path):
        return None
    
    # Try MoviePy (most reliable if installed)
    try:
        from moviepy import AudioFileClip
        # Use context manager to ensure file handle is closed
        with AudioFileClip(audio_path) as audio:
            return audio.duration
    except Exception:
        pass
    
    # Fallback: parse duration from ffmpeg output
    try:
        result = subprocess.run(
            [FFMPEG_BINARY, '-i', audio_path],
            capture_output=True,
            text=True
        )
        # Look for "Duration: 00:00:00.00" in stderr
        output = result.stderr
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
        if match:
            h, m, s = map(float, match.groups())
            return h * 3600 + m * 60 + s
    except Exception:
        pass
    
    return None


def split_audio_with_ffmpeg(
    audio_path: str,
    chunk_duration_minutes: int = 5,
    output_dir: str | None = None
) -> list[str]:
    """
    Split audio using ffmpeg binary from imageio-ffmpeg.
    Uses stream copy for speed and no re-encoding.
    """
    if not os.path.isfile(audio_path):
        return []
    
    duration = get_audio_duration(audio_path)
    if not duration:
        return []
    
    chunk_duration_seconds = chunk_duration_minutes * 60
    
    if duration <= chunk_duration_seconds:
        return [audio_path]
    
    output_dir = output_dir or os.path.dirname(audio_path)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    base_name = Path(audio_path).stem
    extension = Path(audio_path).suffix
    
    chunks = []
    start_time = 0
    chunk_index = 1
    
    while start_time < duration:
        chunk_duration = min(chunk_duration_seconds, duration - start_time)
        
        chunk_filename = f"{base_name}_chunk_{chunk_index:03d}{extension}"
        chunk_path = os.path.join(output_dir, chunk_filename)
        
        # Build ffmpeg command using the binary path
        cmd = [
            FFMPEG_BINARY,
            '-y',             # Overwrite output
            '-i', audio_path, # Input file
            '-ss', str(start_time),
            '-t', str(chunk_duration),
            '-c', 'copy',     # Stream copy (fast, no re-encoding)
            chunk_path
        ]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True
            )
            chunks.append(chunk_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"FFmpeg split error: {e}")
            return []  # ffmpeg failed
        
        start_time += chunk_duration_seconds
        chunk_index += 1
    
    return chunks


def split_audio_into_chunks(
    audio_path: str,
    chunk_duration_minutes: int = 5,
    output_dir: str | None = None
) -> list[str]:
    """
    Split audio file into chunks. 
    Relies on imageio-ffmpeg binary which is guaranteed to be present with moviepy.
    """
    # Try ffmpeg split (using imageio-ffmpeg binary)
    chunks = split_audio_with_ffmpeg(audio_path, chunk_duration_minutes, output_dir)
    if chunks:
        return chunks
    
    # If all fail, return single file
    return [audio_path] if os.path.isfile(audio_path) else []


def get_chunk_info(audio_path: str, chunk_duration_minutes: int = 5) -> dict:
    """
    Get information about how an audio file would be chunked.
    
    Returns dict with: duration, num_chunks, chunk_duration
    """
    duration = get_audio_duration(audio_path)
    if not duration:
        return {"duration": 0, "num_chunks": 0, "chunk_duration": 0}
    
    chunk_duration_seconds = chunk_duration_minutes * 60
    num_chunks = max(1, int((duration + chunk_duration_seconds - 1) / chunk_duration_seconds))
    
    return {
        "duration": duration,
        "num_chunks": num_chunks,
        "chunk_duration": chunk_duration_minutes
    }
