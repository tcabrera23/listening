# Sistema de División de Audio para Videos Largos

## Problema

Cuando un video de YouTube es muy largo (>5 minutos), el archivo de audio resultante puede exceder el límite de Groq Whisper API (~25MB). Por ejemplo, un video de 55 minutos genera un archivo M4A de ~51.7MB.

**Error típico:** `Error code: 413 - Request Entity Too Large`

## Solución Implementada

La aplicación ahora divide automáticamente los audios largos en segmentos de 5 minutos y transcribe cada uno por separado. Cada segmento se muestra en una pestaña independiente con su propio ejercicio de fill-in-the-blanks.

## Métodos de División

### 1. **ffmpeg (Recomendado - Rápido)**

Si `ffmpeg` está instalado, se usa stream copy (sin re-codificación), lo cual es MUY rápido:

```bash
# Windows (con Chocolatey)
choco install ffmpeg

# O descarga desde: https://ffmpeg.org/download.html
# Agregar a PATH: C:\ffmpeg\bin
```

**Ventajas:**
- Velocidad: cortar 55 min de audio toma ~2 segundos
- Sin pérdida de calidad (stream copy)
- Menor tamaño de archivos

### 2. **Fallback - Sin división**

Si `ffmpeg` no está disponible:
- Se intenta transcribir el archivo completo
- Si falla por tamaño (413), se muestra error con instrucciones

## Flujo de la Aplicación

```
┌─────────────────────────────────────────┐
│ Usuario pega URL de YouTube            │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Descarga audio (yt-dlp, nativo M4A)    │
│ Se guarda en cache: files/VIDEO_ID.m4a │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Analiza duración con ffprobe/pydub     │
│ Calcula # de segmentos (5 min c/u)     │
└─────────────┬───────────────────────────┘
              │
       ┌──────┴──────┐
       │ >5 minutos? │
       └──────┬──────┘
              │
       ┌──────┴───────────┐
       │                  │
    SÍ │                  │ NO
       │                  │
       ▼                  ▼
┌─────────────┐    ┌──────────────┐
│ Dividir con │    │ Transcribir  │
│ ffmpeg      │    │ directamente │
│ (stream     │    └──────────────┘
│  copy)      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Transcribir cada segmento con Groq     │
│ (paralelo: chunk_001.m4a, chunk_002...)│
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Generar ejercicios para cada segmento  │
│ (LLM: Groq/OpenRouter)                  │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ UI: Tabs con segmentos (0-5min, 5-10...) │
│ Cada tab: transcripción + ejercicio    │
└─────────────────────────────────────────┘
```

## Estructura de Archivos

```
files/
├── VIDEO_ID.m4a              # Audio original (cache)
├── VIDEO_ID_chunk_001.m4a    # Segmento 1 (0-5 min)
├── VIDEO_ID_chunk_002.m4a    # Segmento 2 (5-10 min)
├── VIDEO_ID_chunk_003.m4a    # Segmento 3 (10-15 min)
...
└── VIDEO_ID_chunk_012.m4a    # Segmento 12 (55-56 min)
```

## Ejemplo: Video de 55 Minutos

- **Audio original:** 51.7 MB (demasiado grande para Groq)
- **Segmentos:** 12 archivos de ~4.3 MB cada uno
- **Proceso:**
  1. Descarga: 15 segundos
  2. División (ffmpeg): 2 segundos
  3. Transcripción: ~30 segundos (12 segmentos en paralelo)
  4. Generación de ejercicios: ~20 segundos

**Total:** ~1 minuto

## API de Transcripción

### Función Principal

```python
from transcribe import transcribe_audio_by_segments

# Transcribe y retorna lista de textos por segmento
transcriptions, error = transcribe_audio_by_segments(
    audio_path="files/VIDEO_ID.m4a",
    provider="groq"
)

# transcriptions = [
#     "Segment 1 text...",
#     "Segment 2 text...",
#     ...
# ]
```

### Función Combinada (Legado)

```python
from transcribe import transcribe_audio

# Transcribe y concatena todos los segmentos
text, error = transcribe_audio(
    audio_path="files/VIDEO_ID.m4a",
    provider="groq"
)
# text = "Segment 1 text...\n\nSegment 2 text..."
```

## Streamlit Cloud

Para que funcione en Streamlit Cloud, agrega `ffmpeg` a `packages.txt`:

```txt
ffmpeg
```

Streamlit Cloud instalará `ffmpeg` automáticamente usando apt-get (Ubuntu).

## Troubleshooting

### Error: "No se pudieron crear los segmentos de audio"

**Causa:** `ffmpeg` no está instalado o no está en PATH

**Solución:**
1. Instala `ffmpeg` (ver arriba)
2. Verifica instalación: `ffmpeg -version`
3. Agrega a PATH si es necesario

### Error: "Error 413: Request Entity Too Large"

**Causa:** Archivo de audio muy grande + ffmpeg no disponible

**Solución:**
- Instala `ffmpeg` para habilitar división automática
- O usa un video más corto (<5 minutos)

### Los segmentos no se generan

**Diagnóstico:**
```python
from audio_splitter import get_chunk_info

info = get_chunk_info("files/VIDEO_ID.m4a", chunk_duration_minutes=5)
print(info)
# {'duration': 3348.5, 'num_chunks': 12, 'chunk_duration': 5}
```

Si `num_chunks == 0`, el archivo no se puede leer (corrupto o formato no soportado).

## Notas

- Los segmentos se crean en el mismo directorio que el audio original (`files/`)
- Los archivos de segmentos se mantienen en caché (no se recrean si ya existen)
- Para limpiar cache: usa el botón "Limpiar caché" en la barra lateral de la app
