"""
Milix - English practice with YouTube: Listening and Fill the Blanks.
"""
import os
import re
import json
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from blanks import generate_blanks
from transform_video import get_audio_from_youtube

load_dotenv()

st.set_page_config(page_title="Milix - Listening & Fill the Blanks", layout="wide")

def init_session_state():
    if "transcriptions" not in st.session_state:
        st.session_state.transcriptions = []  # List of transcriptions per segment
    if "blanks_data_list" not in st.session_state:
        st.session_state.blanks_data_list = []  # List of blanks_data per segment
    if "user_answers_list" not in st.session_state:
        st.session_state.user_answers_list = []  # List of user_answers per segment
    if "total_score" not in st.session_state:
        st.session_state.total_score = 0
    if "last_score" not in st.session_state:
        st.session_state.last_score = None
    if "work_dir" not in st.session_state:
        st.session_state.work_dir = None


def normalize_answer(s: str) -> str:
    return (s or "").strip().lower()


def compare_answers(user_list: list[str], correct_list: list[str]) -> tuple[int, int]:
    """Return (correct_count, total)."""
    correct_list = [normalize_answer(a) for a in correct_list]
    user_list = [normalize_answer(u) for u in user_list]
    total = len(correct_list)
    correct = sum(1 for u, c in zip(user_list, correct_list) if u == c)
    return correct, total


def render_listening_tab():
    st.title("Milix – Listening & Fill the Blanks")
    st.markdown("Pega un enlace de YouTube para generar un ejercicio de comprensión auditiva.")

    col_config1, col_config2 = st.columns([2, 1])
    with col_config1:
        url = st.text_input("URL de YouTube", placeholder="https://www.youtube.com/watch?v=...")
    with col_config2:
        provider = st.selectbox(
            "Proveedor de IA",
            ["openai", "groq", "openrouter", "auto"],
            format_func=lambda x: {
                "groq": "Groq (Rápido, requiere ffmpeg)",
                "openai": "OpenAI (Whisper + GPT-4o-mini)",
                "openrouter": "OpenRouter (Gemini)",
                "auto": "Auto (Prueba todos)"
            }[x],
            help="Selecciona el proveedor de IA para transcripción y generación de ejercicios"
        )
    
    ui_col1, ui_col2, ui_col3 = st.columns(3)
    with ui_col1:
        num_blanks = st.slider(
            "Cantidad de huecos en el ejercicio",
            min_value=1,
            max_value=30,
            value=10,
            help="Cantidad total de blanks por segmento",
        )
    with ui_col2:
        difficulty = st.selectbox(
            "Nivel objetivo",
            ["C1", "C2"],
            help="C2 prioriza vocabulario más complejo",
        )
    with ui_col3:
        max_blanks_per_sentence = st.slider(
            "Máx. huecos por oración/cadena",
            min_value=1,
            max_value=3,
            value=2,
            help="Permite densidad alta en la misma oración",
        )

    if st.button("Procesar vídeo"):
        if not url or "youtube" not in url.lower():
            st.error("Introduce una URL válida de YouTube.")
            return
        
        # Check if cached
        from transform_video import _get_video_id_from_url, _get_cached_audio, CACHE_DIR
        video_id = _get_video_id_from_url(url)
        cached_audio = _get_cached_audio(video_id) if video_id else None
        
        if cached_audio:
            st.info(f"✨ Audio en caché encontrado: {os.path.basename(cached_audio)}")
            audio_path = cached_audio
        else:
            with st.spinner("Descargando y extrayendo audio..."):
                work_dir = tempfile.mkdtemp()
                st.session_state.work_dir = work_dir
                audio_path, error_msg = get_audio_from_youtube(url, work_dir, use_cache=True)
        
        if not audio_path:
            st.error("❌ No se pudo obtener el audio del vídeo.")
            if error_msg:
                st.error(f"Detalle del error: {error_msg}")
            st.info("💡 Intenta con otro video de YouTube o verifica que el video sea público.")
            return
        
        if not cached_audio:
            st.success(f"✅ Audio descargado y guardado en caché: {os.path.basename(audio_path)}")
        
        # Check audio duration and segments
        from audio_splitter import get_chunk_info
        audio_info = get_chunk_info(audio_path, chunk_duration_minutes=5)
        num_segments = audio_info.get("num_chunks", 1)
        duration_min = audio_info.get("duration", 0) / 60
        
        if num_segments > 1:
            st.info(f"📹 Video largo detectado ({duration_min:.1f} min). Se dividirá en {num_segments} segmentos de ~5 min")
        
        with st.spinner(f"Transcribiendo con {provider.upper()}... (esto puede tomar unos minutos)"):
            from transcribe import transcribe_audio_by_segments
            
            # Check for cached transcription
            transcription_cache_path = CACHE_DIR / f"{video_id}_transcription.json"
            if transcription_cache_path.exists():
                try:
                    with open(transcription_cache_path, "r", encoding="utf-8") as f:
                        transcriptions = json.load(f)
                    error = None
                    st.info("📄 Transcripción cargada desde caché local")
                except Exception:
                    transcriptions, error = transcribe_audio_by_segments(audio_path, provider)
            else:
                transcriptions, error = transcribe_audio_by_segments(audio_path, provider)
                if transcriptions:
                    try:
                        with open(transcription_cache_path, "w", encoding="utf-8") as f:
                            json.dump(transcriptions, f)
                    except Exception as e:
                        print(f"Error saving transcription cache: {e}")
        
        if not transcriptions:
            st.error(f"❌ No se pudo transcribir el audio.")
            if error:
                st.error(f"**Error detallado:** {error}")
            with st.expander("🔧 Soluciones posibles"):
                st.markdown("""
                **Si usas Groq:**
                - Verifica que `GROQ_API_KEY` en `.env` sea válida
                - Obtén una nueva key en: https://console.groq.com/keys
                - **Requiere ffmpeg instalado** para videos largos
                
                **Si usas OpenAI:**
                - Verifica que `OPENAI_API_KEY` en `.env` sea válida
                - Obtén una key en: https://platform.openai.com/api-keys
                - Usa Whisper-1 para transcripción (más estable)
                
                **Si el audio es muy largo:**
                - La app automáticamente divide en segmentos de 5 minutos
                - Requiere `ffmpeg` instalado en el sistema
                - Cada segmento se transcribe por separado
                
                **Prueba con 'Auto'** para que intente todos los proveedores.
                **Recomendación:** Usa OpenAI para mejor estabilidad.
                """)
            return
        
        st.success(f"✅ Transcripción completada ({len(transcriptions)} segmento(s), {sum(len(t) for t in transcriptions)} caracteres)")
        st.session_state.transcriptions = transcriptions
        
        with st.spinner(f"Generando ejercicios con {provider.upper()}..."):
            blanks_data_list = []
            for i, trans in enumerate(transcriptions, 1):
                blanks_data = generate_blanks(
                    trans,
                    num_blanks,
                    provider,
                    difficulty=difficulty,
                    max_blanks_per_sentence=max_blanks_per_sentence,
                )
                if not blanks_data:
                    st.warning(f"⚠️ No se pudo generar ejercicio para segmento {i}")
                    blanks_data_list.append(None)
                else:
                    blanks_data_list.append(blanks_data)
        
        valid_exercises = sum(1 for b in blanks_data_list if b is not None)
        if valid_exercises == 0:
            st.error("❌ No se pudieron generar ejercicios.")
            st.info("💡 Intenta cambiar el proveedor de IA o reduce el número de huecos.")
            return
        
        st.success(f"✅ {valid_exercises} ejercicio(s) generado(s)")
        st.session_state.blanks_data_list = blanks_data_list
        st.session_state.user_answers_list = [[] for _ in blanks_data_list]
        st.rerun()

    # Layout: Exercise on top, Optional Transcript below
    
    if not st.session_state.transcriptions:
        st.info("👆 Procesa un video para comenzar")
    else:
        # Create tabs for each segment
        num_segments = len(st.session_state.transcriptions)
    
        if num_segments == 1:
            # Single segment
            transcription = st.session_state.transcriptions[0]
            blanks_data = st.session_state.blanks_data_list[0] if st.session_state.blanks_data_list else None
            
            if blanks_data:
                _render_blanks_exercise(blanks_data, 0)
            
            st.divider()
            show_transcript = st.checkbox("👀 Ver transcripción original", key="show_trans_0")
            if show_transcript:
                st.info(transcription)
        
        else:
            # Multiple segments: use tabs
            tab_labels = [f"Segmento {i+1} (~{i*5}-{(i+1)*5} min)" for i in range(num_segments)]
            tabs = st.tabs(tab_labels)
            
            for i, tab in enumerate(tabs):
                with tab:
                    transcription = st.session_state.transcriptions[i]
                    blanks_data = st.session_state.blanks_data_list[i] if i < len(st.session_state.blanks_data_list) else None
                    
                    if blanks_data:
                        _render_blanks_exercise(blanks_data, i)
                    else:
                        st.warning("No se pudo generar ejercicio para este segmento")
                    
                    st.divider()
                    show_transcript = st.checkbox("👀 Ver transcripción original", key=f"show_trans_{i}")
                    if show_transcript:
                        st.info(transcription)


def _render_blanks_exercise(blanks_data: dict, segment_idx: int):
    """Render fill-the-blanks exercise for a segment."""
    text = blanks_data["text_with_blanks"]
    answers = blanks_data["answers"]
    parts = re.split(r"__+", text)
    
    if len(parts) != len(answers) + 1:
        st.warning("El número de huecos no coincide con las respuestas.")
        st.write(text)
        return
    
    st.subheader("Completa los huecos")
    
    # Render text with markers
    display_parts = []
    for i, p in enumerate(parts):
        display_parts.append(p)
        if i < len(answers):
            display_parts.append(f" **[{i+1}]** ")
    st.markdown("".join(display_parts))
    
    st.markdown("---")
    st.caption("Escribe tus respuestas:")
    
    # Render inputs in a grid (3 columns)
    cols = st.columns(3)
    
    # Build user answers for this segment
    current_answers = []
    for i in range(len(answers)):
        col = cols[i % 3]
        val = col.text_input(f"Hueco {i+1}", key=f"seg{segment_idx}_blank_{i}")
        current_answers.append(val)
    
    # Update session state for this segment
    # Ensure list is long enough
    while len(st.session_state.user_answers_list) <= segment_idx:
        st.session_state.user_answers_list.append([])
        
    st.session_state.user_answers_list[segment_idx] = current_answers
    
    if st.button("Ver corrección", key=f"seg{segment_idx}_check"):
        correct, total = compare_answers(current_answers, answers)
        st.session_state.total_score += correct
        
        if correct == total:
            st.success(f"🎉 ¡Perfecto! {correct}/{total} aciertos.")
        else:
            st.warning(f"Has acertado {correct} de {total}.")
            
        with st.expander("Ver respuestas correctas"):
            for i, a in enumerate(answers):
                u = current_answers[i] if i < len(current_answers) else ""
                ok = normalize_answer(u) == normalize_answer(a)
                icon = "✅" if ok else "❌"
                st.write(f"**{i+1}.** {icon} Correcta: **{a}**" + (f" (Tú: {u})" if u and not ok else ""))

def main():
    init_session_state()
    
    # Sidebar con información de caché
    with st.sidebar:
        st.header("⚙️ Configuración")
        from transform_video import CACHE_DIR
        
        if CACHE_DIR.exists():
            cached_files = list(CACHE_DIR.glob("*"))
            audio_files = [f for f in cached_files if f.suffix in (".mp3", ".m4a", ".webm", ".ogg", ".wav")]
            
            st.metric("Audios en caché", len(audio_files))
            
            if audio_files:
                total_size = sum(f.stat().st_size for f in audio_files) / (1024 * 1024)
                st.metric("Tamaño total", f"{total_size:.2f} MB")
                
                with st.expander("Ver archivos en caché"):
                    for f in audio_files[:10]:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        st.text(f"{f.name[:30]}... ({size_mb:.1f}MB)")
                    if len(audio_files) > 10:
                        st.caption(f"...y {len(audio_files) - 10} más")
                
                if st.button("🗑️ Limpiar caché", type="secondary"):
                    import shutil
                    try:
                        shutil.rmtree(CACHE_DIR)
                        CACHE_DIR.mkdir(exist_ok=True)
                        st.success("Caché limpiada correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al limpiar caché: {e}")
        
        st.divider()
        st.caption("💡 Los videos descargados se guardan en `files/` para evitar descargas repetidas.")
    
    tab1, tab2 = st.tabs(["Listening – Fill the Blanks", "Modo avanzado C1/C2"])
    with tab1:
        render_listening_tab()
    with tab2:
        st.subheader("Modo avanzado C1/C2")
        st.markdown(
            "Configura el nivel C1/C2 y el máximo de huecos por oración en la pestaña principal. "
            "Para mayor dificultad, usa C2 con 2-3 huecos por oración/cadena."
        )
        if st.session_state.get("total_score", 0) > 0:
            st.metric("Puntos acumulados (esta sesión)", st.session_state.total_score)


if __name__ == "__main__":
    main()
