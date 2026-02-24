"""
Download YouTube video and extract audio for transcription.
Uses yt-dlp first; falls back to moviepy if extraction fails.
Implements caching system to avoid re-downloading videos.
"""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import yt_dlp


CACHE_DIR = Path(__file__).parent / "files"
CACHE_DIR.mkdir(exist_ok=True)


def _get_video_id_from_url(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("id") if info else None
    except Exception:
        # Fallback: use hash of URL
        return hashlib.md5(url.encode()).hexdigest()[:16]


def _get_cached_audio(video_id: str) -> str | None:
    """Check if audio file exists in cache. Returns path or None."""
    if not video_id:
        return None
    for ext in (".mp3", ".m4a", ".webm", ".ogg", ".wav"):
        cached_file = CACHE_DIR / f"{video_id}{ext}"
        if cached_file.exists():
            return str(cached_file)
    return None


def _save_to_cache(source_path: str, video_id: str) -> str | None:
    """Copy audio file to cache directory. Returns cached path or None."""
    if not source_path or not video_id or not os.path.isfile(source_path):
        return None
    try:
        ext = Path(source_path).suffix
        cached_path = CACHE_DIR / f"{video_id}{ext}"
        shutil.copy2(source_path, cached_path)
        return str(cached_path)
    except Exception:
        return None


def _find_audio_file(out_dir: str) -> str | None:
    for name in os.listdir(out_dir):
        if name.lower().endswith((".mp3", ".m4a", ".webm", ".ogg", ".wav", ".mpeg", ".mpga")):
            return os.path.join(out_dir, name)
    return None


def _get_audio_native_with_yt_dlp(url: str, out_dir: str) -> tuple[str | None, str | None]:
    """
    Download audio stream without ffmpeg postprocessing.
    Returns (path, error_message).
    """
    out_path = os.path.join(out_dir, "%(title)s.%(ext)s")
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "outtmpl": out_path,
        "noplaylist": True,
        "retries": 5,
        "extractor_args": {"youtube": {"player_client": ["default", "android", "web"]}},
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None, "No video info returned"
        path = _find_audio_file(out_dir)
        return path, None
    except Exception as e:
        return None, str(e)


def _get_audio_mp3_with_yt_dlp(url: str, out_dir: str) -> tuple[str | None, str | None]:
    """Try to download and extract audio to MP3 using yt-dlp+ffmpeg."""
    if not shutil.which("ffmpeg"):
        return None, "ffmpeg not found in PATH"
    out_path = os.path.join(out_dir, "%(title)s.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "noplaylist": True,
        "retries": 5,
        "extractor_args": {"youtube": {"player_client": ["default", "android", "web"]}},
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None, "No video info returned"
        path = _find_audio_file(out_dir)
        return path, None
    except Exception as e:
        return None, str(e)


def _get_audio_with_moviepy(video_path: str, out_dir: str) -> tuple[str | None, str | None]:
    """Extract audio from downloaded video using moviepy."""
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip
    except ImportError as e:
        return None, f"MoviePy import error: {e}"
        
    out_audio = os.path.join(out_dir, "audio_from_video.mp3")
    try:
        # Prefer VideoFileClip so we support any video file
        with VideoFileClip(video_path) as clip:
            clip.audio.write_audiofile(out_audio, logger=None)
        return (out_audio, None) if os.path.isfile(out_audio) else (None, "MoviePy failed to write audio")
    except Exception as e:
        try:
            with AudioFileClip(video_path) as clip:
                clip.write_audiofile(out_audio, logger=None)
            return (out_audio, None) if os.path.isfile(out_audio) else (None, "MoviePy fallback failed")
        except Exception as e2:
            return None, f"MoviePy error: {e}, Fallback error: {e2}"


def _download_video_only(url: str, out_dir: str) -> tuple[str | None, str | None]:
    """Download video as a single file without forcing merge."""
    out_path = os.path.join(out_dir, "%(title)s.%(ext)s")
    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": out_path,
        "noplaylist": True,
        "retries": 5,
        "extractor_args": {"youtube": {"player_client": ["default", "android", "web"]}},
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None, "No info"
            path = ydl.prepare_filename(info)
            full = os.path.join(out_dir, os.path.basename(path))
            return (full, None) if os.path.isfile(full) else (None, "Video file not found after download")
    except Exception as e:
        return None, str(e)


def get_audio_from_youtube(url: str, work_dir: str | None = None, use_cache: bool = True) -> tuple[str | None, str | None]:
    """
    Download YouTube video and return path to an audio file.
    Returns (path, error_message).
    """
    # Check cache first
    if use_cache:
        try:
            video_id = _get_video_id_from_url(url)
            if video_id:
                cached_audio = _get_cached_audio(video_id)
                if cached_audio:
                    return cached_audio, None
        except Exception as e:
            print(f"Cache check error: {e}")
            video_id = None
    
    # Not in cache, download
    directory = work_dir or tempfile.mkdtemp()
    Path(directory).mkdir(parents=True, exist_ok=True)
    
    errors = []

    # Strategy 1: Native
    path, err = _get_audio_native_with_yt_dlp(url, directory)
    if path:
        if use_cache and video_id:
            _save_to_cache(path, video_id)
        return path, None
    errors.append(f"Native: {err}")

    # Strategy 2: MP3 (ffmpeg)
    path, err = _get_audio_mp3_with_yt_dlp(url, directory)
    if path:
        if use_cache and video_id:
            _save_to_cache(path, video_id)
        return path, None
    errors.append(f"FFmpeg: {err}")

    # Strategy 3: MoviePy
    video_path, vid_err = _download_video_only(url, directory)
    if video_path:
        path, err = _get_audio_with_moviepy(video_path, directory)
        if path:
            if use_cache and video_id:
                _save_to_cache(path, video_id)
            return path, None
        errors.append(f"MoviePy extraction: {err}")
    else:
        errors.append(f"Video download: {vid_err}")

    return None, "; ".join(errors)
