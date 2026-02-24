import imageio_ffmpeg
print(f"FFmpeg binary: {imageio_ffmpeg.get_ffmpeg_exe()}")

import subprocess
try:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run([exe, '-version'], capture_output=True, text=True)
    print("FFmpeg runs ok!")
    print(result.stdout.splitlines()[0])
except Exception as e:
    print(f"Error running ffmpeg: {e}")
