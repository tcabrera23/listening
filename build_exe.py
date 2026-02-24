import os
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all, copy_metadata

APP_NAME = "Milix_Listening"
MAIN_SCRIPT = "run_app.py"

# Archivos de la app
ADD_DATA = [
    ("app.py", "."),
    ("blanks.py", "."),
    ("transcribe.py", "."),
    ("transform_video.py", "."),
    ("audio_splitter.py", "."),
    (".env.example", "."),
]

# --- Recolectar dependencias complejas ---
all_datas = []
all_binaries = []
all_hiddenimports = []

for pkg in ['moviepy', 'imageio_ffmpeg', 'imageio', 'streamlit']:
    try:
        d, b, h = collect_all(pkg)
        all_datas.extend(d)
        all_binaries.extend(b)
        all_hiddenimports.extend(h)
    except Exception as e:
        print(f"WARN: collect_all('{pkg}') failed: {e}")

# --- Copiar metadatos de TODOS los paquetes que lo necesitan ---
for pkg in [
    'streamlit', 'imageio', 'imageio_ffmpeg', 'moviepy',
    'numpy', 'pandas', 'pyarrow', 'altair',
    'pydub', 'yt-dlp', 'openai', 'importlib_metadata',
    'packaging', 'tqdm', 'requests', 'rich',
]:
    try:
        all_datas.extend(copy_metadata(pkg))
    except Exception:
        pass  # Package might not be installed, skip

# Hidden imports explícitos
extra_hidden = [
    "streamlit.web.cli",
    "altair.vegalite.v5",
    "moviepy.editor",
    "moviepy.audio.fx.all",
    "moviepy.video.fx.all",
    "proglog",
    "dotenv",
]
all_hiddenimports.extend(extra_hidden)

# Ruta de streamlit para sus archivos estáticos (HTML/JS/CSS)
import streamlit
streamlit_path = os.path.dirname(streamlit.__file__)

args = [
    MAIN_SCRIPT,
    f"--name={APP_NAME}",
    "--onefile",
    "--clean",
    "--noconfirm",
    f"--add-data={streamlit_path}{os.pathsep}streamlit",
    *[f"--add-data={src}{os.pathsep}{dst}" for src, dst in ADD_DATA],
    *[f"--add-data={src}{os.pathsep}{dst}" for src, dst in all_datas],
    *[f"--add-binary={src}{os.pathsep}{dst}" for src, dst in all_binaries],
    *[f"--hidden-import={h}" for h in all_hiddenimports],
]

print(f"Generando {APP_NAME}.exe ...")
print(f"  {len(all_datas)} data entries")
print(f"  {len(all_binaries)} binary entries")
print(f"  {len(all_hiddenimports)} hidden imports")
PyInstaller.__main__.run(args)
print(f"\nListo! Ejecutable en dist/{APP_NAME}.exe")
