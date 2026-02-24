El objetivo de mi aplicacion es que las personas que quieran practicar ingles con videos a traves de links de youtube, puedan realizar ejercicios personalizados. Como primer caso de uso, solo implementaremos la tematica de Listening y Fill the Blanks. 

## Flujo de la App

1 - Usuario pega link de youtube
2 - Funcion que descarga el video, toma el mp3 y genera la transcripcion con whisper (con **caché automático** en `files/`)
3 - LLM que analiza la transcripcion, para de forma inteligente reemplazar una palabra clave en el listening por '__' y guarda la palabra reemplazada para luego mostrar las respuestas correctas. El nuevo texto con los campos vacios a completar se muestra por pantalla. 
4 - Una vez que el usuario finaliza, hace click en ver correcion y la aplicacion compara lo escrito por la persona versus lo que tenia el LLM. Debes aplicar condicionales basicos y acumular los puntos del usuario.

## Sistema de Caché

✨ **Nuevo:** Los videos descargados se guardan automáticamente en `files/` para evitar descargas repetidas.

- Primera descarga: guarda en caché
- Descargas siguientes: carga instantánea desde caché
- Gestión de caché desde el sidebar de la app
- Ver más: [CACHE_SYSTEM.md](CACHE_SYSTEM.md) 

Podes inspirarte en ejercicios de paginas como cambridge. Como complemento del texto, podes tener una reserva de 5-10 oraciones para practicar el fill the blanks en otra seccion y con las palabras correctas disponibles en un lado. Podes agregar dificultad como: 
- easy: 1 blank a completar
- mid: 2 blank a completar
- high: 3-5 blank a completar
pista opcional de una palabra por oracion en dificultad high. 

Quiero una interfaz clara en streamlit, con un titulo y en el centro dos divisiones con: 
- panel izquierdo: bloque del texto del ejercicio a completar. recomiendo dejar la transcripcion completa a un 75% pero que sea personalizable por el usuario
- panel derecho: seccion de oraciones: 
- **sidebar**: información de caché y gestión de archivos descargados

nota: a medida que avance la app, voy a ir agregando otras pestañas con otras categorias (reading, writing, grammar, etc)

## Archivos Importantes

- `app.py` - Aplicación Streamlit principal
- `transform_video.py` - Descarga de YouTube con sistema de caché
- `transcribe.py` - Transcripción con Groq Whisper / OpenRouter
- `blanks.py` - Generación de ejercicios con LLM
- `files/` - Caché de audios descargados (auto-creada)
- `CACHE_SYSTEM.md` - Documentación del sistema de caché
- `SETUP_API_KEYS.md` - Guía de configuración de API keys