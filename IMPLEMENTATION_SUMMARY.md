# Implementación Completa: Sistema de Segmentación de Audio

## Cambios Realizados

### ✅ 1. Nuevo Módulo: `audio_splitter.py`

**Propósito:** Dividir archivos de audio largos en segmentos de 5 minutos para evitar el error 413 de Groq.

**Funciones principales:**
- `get_audio_duration(audio_path)` - Obtiene duración del audio
- `split_audio_with_ffmpeg(audio_path, chunk_duration_minutes, output_dir)` - División rápida con ffmpeg (sin re-codificación)
- `split_audio_into_chunks(audio_path, chunk_duration_minutes, output_dir)` - API principal de división
- `get_chunk_info(audio_path, chunk_duration_minutes)` - Info sobre segmentación

**Estrategia de división:**
1. **ffmpeg (preferido):** Stream copy, muy rápido, sin pérdida de calidad
2. **Fallback:** Retorna archivo completo (error 413 manejado en transcribe.py)

### ✅ 2. Actualizado: `transcribe.py`

**Nuevas funciones:**

```python
def transcribe_audio_by_segments(audio_path, provider="groq"):
    """
    Transcribe audio y retorna lista de transcripciones por segmento.
    Divide automáticamente si archivo > 20MB.
    Returns: (list[str] | None, error_msg | None)
    """
```

**Lógica mejorada:**
- Detecta archivos grandes (> 20MB)
- Divide automáticamente con `audio_splitter`
- Transcribe cada segmento secuencialmente
- Maneja errores por segmento (ej: "Error en segmento 3/12: ...")
- Retorna lista de transcripciones O error específico

**Compatibilidad:**
- `transcribe_audio()` sigue funcionando (concatena todos los segmentos)
- `transcribe_audio_by_segments()` retorna lista para UI multi-tab

### ✅ 3. Actualizado: `app.py`

**Session State modificado:**

```python
# Antes
st.session_state.transcription  # str
st.session_state.blanks_data     # dict
st.session_state.user_answers    # list

# Ahora
st.session_state.transcriptions      # list[str]
st.session_state.blanks_data_list    # list[dict | None]
st.session_state.user_answers_list   # list[list[str]]
```

**Nueva UI: Tabs por segmento**

```
┌───────────────────────────────────────────────────┐
│ [Segmento 1 (0-5 min)] [Seg 2 (5-10)] [Seg 3...] │
├───────────────────────────────────────────────────┤
│ Transcripción segmento 1                          │
│ ─────────────────────────────────────────────────│
│ [Ejercicio Fill-in-the-Blanks]                    │
│ [ ] Hueco 1: _______                              │
│ [ ] Hueco 2: _______                              │
│ [Ver corrección]                                  │
└───────────────────────────────────────────────────┘
```

**Flujo actualizado:**

1. Usuario pega URL de YouTube
2. App descarga audio (cache en `files/`)
3. App analiza duración → calcula # segmentos
4. Si > 5 min: muestra info (`"Video largo: 55.8 min, se dividirá en 12 segmentos"`)
5. Transcribe cada segmento con Groq (muestra progreso)
6. Genera ejercicio para cada segmento
7. Muestra tabs: 1 por segmento
8. Usuario completa ejercicios independientemente

### ✅ 4. Nueva función: `_render_blanks_exercise(blanks_data, segment_idx, opacity)`

**Propósito:** Renderizar ejercicio de un segmento específico.

**Features:**
- Inputs con keys únicas por segmento (`seg0_blank_1`, `seg1_blank_1`...)
- Botón de corrección independiente por segmento
- Puntos acumulados por segmento

### ✅ 5. Actualizado: `requirements.txt`

```txt
streamlit>=1.28
openai>=1.0
yt-dlp>=2024.1
moviepy>=1.0.3
python-dotenv>=1.0
pydub>=0.25.1  # ← NUEVO (usado para detección de duración si ffmpeg no disponible)
```

### ✅ 6. Documentación creada

- `AUDIO_SPLITTING.md` - Guía completa del sistema de división
- `SETUP_API_KEYS.md` (existente) - Cómo configurar Groq API key
- `CACHE_SYSTEM.md` (existente) - Funcionamiento del cache

## Ejemplo de Uso

### Video Corto (<5 min)

```python
# URL: https://www.youtube.com/watch?v=SHORT_VIDEO
# Audio: files/SHORT_VIDEO.m4a (3.2 MB)
# Transcripción: 1 segmento
# UI: Sin tabs, ejercicio único
```

### Video Largo (55 min)

```python
# URL: https://www.youtube.com/watch?v=Iz9HydQZhPo
# Audio: files/Iz9HydQZhPo.m4a (51.7 MB)
# División: 12 segmentos × 5 min = 60 min
#   - files/Iz9HydQZhPo_chunk_001.m4a (4.3 MB)
#   - files/Iz9HydQZhPo_chunk_002.m4a (4.3 MB)
#   - ... × 12
# Transcripción: 12 segmentos transcriptos
# UI: 12 tabs, 1 ejercicio por tab
```

## Ejemplo de Código

### Transcribir por segmentos

```python
from transcribe import transcribe_audio_by_segments

transcriptions, error = transcribe_audio_by_segments(
    "files/Iz9HydQZhPo.m4a",
    provider="groq"
)

if transcriptions:
    for i, trans in enumerate(transcriptions, 1):
        print(f"Segmento {i}: {len(trans)} chars")
        # Segmento 1: 1842 chars
        # Segmento 2: 1923 chars
        # ...
else:
    print(f"Error: {error}")
```

### Generar ejercicios por segmento

```python
from blanks import generate_blanks

blanks_list = []
for trans in transcriptions:
    blanks_data = generate_blanks(trans, num_blanks=5, provider="groq")
    blanks_list.append(blanks_data)

# blanks_list[0] = {
#     "text_with_blanks": "The cat sat on the __.",
#     "answers": ["mat"],
#     "original": "The cat sat on the mat."
# }
```

## Flujo Completo en app.py

```python
# 1. Download
audio_path = get_audio_from_youtube(url, use_cache=True)

# 2. Check segments
from audio_splitter import get_chunk_info
info = get_chunk_info(audio_path, chunk_duration_minutes=5)
num_segments = info["num_chunks"]

# 3. Transcribe by segments
from transcribe import transcribe_audio_by_segments
transcriptions, error = transcribe_audio_by_segments(audio_path, provider)

# 4. Generate blanks for each segment
blanks_data_list = []
for trans in transcriptions:
    blanks = generate_blanks(trans, num_blanks, provider)
    blanks_data_list.append(blanks)

# 5. Store in session
st.session_state.transcriptions = transcriptions
st.session_state.blanks_data_list = blanks_data_list

# 6. Render tabs
if num_segments > 1:
    tabs = st.tabs([f"Segmento {i+1}" for i in range(num_segments)])
    for i, tab in enumerate(tabs):
        with tab:
            _render_blanks_exercise(blanks_data_list[i], i, opacity)
```

## Testing

### Prueba rápida (sin ffmpeg)

```bash
python test_segments.py
```

**Resultado esperado (SIN ffmpeg):**
```
[TEST 1] Downloading video... [OK]
[TEST 2] Checking audio duration... [OK] 12 segments
[TEST 3] Transcribing... [FAIL] No se pudieron crear segmentos
```

### Prueba completa (CON ffmpeg)

1. Instalar ffmpeg:
   ```bash
   # Windows
   choco install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```

2. Ejecutar test:
   ```bash
   python test_segments.py
   ```

**Resultado esperado (CON ffmpeg):**
```
[TEST 1] Downloading... [OK]
[TEST 2] Duration: 55.8 min, 12 segments [OK]
[TEST 3] Transcribing 12 segments... [OK]
  Segment 1: 1842 chars
  Segment 2: 1923 chars
  ...
[TEST 4] Generating blanks...
  Segment 1: 5 blanks [OK]
  Segment 2: 5 blanks [OK]
  ...
```

## Deployment en Streamlit Cloud

**Archivo `packages.txt`:**
```txt
ffmpeg
```

Streamlit Cloud instalará automáticamente `ffmpeg` al deployar.

## Estado Actual

✅ **Funcionalidades implementadas:**
- División automática de audio (ffmpeg)
- Transcripción por segmentos
- UI multi-tab
- Ejercicios independientes por segmento
- Cache de archivos
- Manejo de errores específico por segmento

⚠️ **Requiere:**
- `ffmpeg` instalado para videos > 5 minutos
- API key de Groq válida (revisar `SETUP_API_KEYS.md`)

## Próximos Pasos

1. **Instalar ffmpeg:** `choco install ffmpeg` (Windows) o añadir a PATH
2. **Verificar API key:** `python diagnose_api.py`
3. **Probar app:** `streamlit run app.py`
4. **Probar video largo:** https://www.youtube.com/watch?v=Iz9HydQZhPo

## Notas Técnicas

- **Límite Groq:** 25MB por archivo (~10 min de audio M4A)
- **Segmentos:** 5 minutos c/u (ajustable en `chunk_duration_minutes`)
- **Formato:** M4A nativo (sin conversión, más rápido)
- **Cache:** `files/` directory (excluido de Git)
- **División:** Stream copy de ffmpeg (sin pérdida, muy rápido)

---

**Autor:** AI Assistant  
**Fecha:** 2026-02-23  
**Versión:** 2.0 (Audio Segmentation)
