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


def _get_audio_native_with_yt_dlp(url: str, out_dir: str) -> str | None:
    """
    Download audio stream without ffmpeg postprocessing.
    This works in environments where ffmpeg is not installed.
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
                return None
        return _find_audio_file(out_dir)
    except Exception:
        return None


def _get_audio_mp3_with_yt_dlp(url: str, out_dir: str) -> str | None:
    """Try to download and extract audio to MP3 using yt-dlp+ffmpeg."""
    if not shutil.which("ffmpeg"):
        return None
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
                return None
        return _find_audio_file(out_dir)
    except Exception:
        return None


def _get_audio_with_moviepy(video_path: str, out_dir: str) -> str | None:
    """Extract audio from downloaded video using moviepy. Returns path to audio file or None."""
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip
    except ImportError:
        return None
    out_audio = os.path.join(out_dir, "audio_from_video.mp3")
    try:
        # Prefer VideoFileClip so we support any video file
        with VideoFileClip(video_path) as clip:
            clip.audio.write_audiofile(out_audio, logger=None)
        return out_audio if os.path.isfile(out_audio) else None
    except Exception:
        try:
            with AudioFileClip(video_path) as clip:
                clip.write_audiofile(out_audio, logger=None)
            return out_audio if os.path.isfile(out_audio) else None
        except Exception:
            return None


def _download_video_only(url: str, out_dir: str) -> str | None:
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
                return None
            path = ydl.prepare_filename(info)
            full = os.path.join(out_dir, os.path.basename(path))
            return full if os.path.isfile(full) else None
    except Exception:
        return None


def get_audio_from_youtube(url: str, work_dir: str | None = None, use_cache: bool = True) -> str | None:
    """
    Download YouTube video and return path to an audio file (MP3 preferred).
    
    Args:
        url: YouTube video URL
        work_dir: Optional working directory (defaults to temp)
        use_cache: If True, check cache first and save downloads to cache
    
    Caching:
        - Files are saved in 'files/' directory with video ID as filename
        - If cached file exists, returns it immediately without downloading
        - New downloads are automatically cached for future use
    
    Fallback strategy:
        - First tries native yt-dlp audio download (no ffmpeg required)
        - Then tries yt-dlp+ffmpeg MP3 extraction when ffmpeg is available
        - If that fails, downloads video with yt-dlp and uses moviepy to extract audio

    Returns path to the audio file, or None on failure.
    """
    # Check cache first
    if use_cache:
        video_id = _get_video_id_from_url(url)
        if video_id:
            cached_audio = _get_cached_audio(video_id)
            if cached_audio:
                return cached_audio
    
    # Not in cache, download
    directory = work_dir or tempfile.mkdtemp()
    Path(directory).mkdir(parents=True, exist_ok=True)

    path = _get_audio_native_with_yt_dlp(url, directory)
    if not path:
        path = _get_audio_mp3_with_yt_dlp(url, directory)
    if not path:
        video_path = _download_video_only(url, directory)
        if video_path:
            path = _get_audio_with_moviepy(video_path, directory)
    
    # Save to cache if successful
    if path and use_cache and video_id:
        cached_path = _save_to_cache(path, video_id)
        if cached_path:
            return cached_path
    
    return path
