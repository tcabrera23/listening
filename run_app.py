import os
import sys
import time
import threading
import webbrowser
from pathlib import Path


def main():
    # Detectar ruta base
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    app_path = base_path / "app.py"

    # Configurar FFmpeg (sin importar imageio a nivel de módulo)
    try:
        import imageio_ffmpeg
        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

    # Configurar Streamlit
    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"

    # Simular argv de streamlit
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
    ]

    # Abrir navegador UNA sola vez, después de que el server arranque
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8501")

    threading.Thread(target=open_browser, daemon=True).start()

    # Ejecutar Streamlit directamente (sin subprocess = sin bucle infinito)
    from streamlit.web import cli as stcli
    stcli.main()


if __name__ == "__main__":
    main()
