# Phase 8 — Multilingual Voice Assistant

## Added
- Browser microphone recording through Streamlit `st.audio_input`.
- Local speech-to-text using `faster-whisper`.
- English, Hindi, and Punjabi transcription hints.
- Text-to-speech responses using gTTS.
- Optional slower speech when Grandma Mode is enabled.
- Voice capability status, transcription, and speech API endpoints.
- Voice API client methods and automated endpoint tests.

## API endpoints
- `GET /api/v1/voice/status`
- `POST /api/v1/voice/transcribe`
- `POST /api/v1/voice/speak`

The main README remains unchanged until Phase 10.
