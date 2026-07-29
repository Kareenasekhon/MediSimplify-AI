# Phase 8 Setup

1. Install backend dependencies:
   `pip install -r backend/requirements.txt`
2. Install frontend dependencies:
   `pip install -r frontend/requirements.txt`
3. Keep the default CPU configuration in `backend/.env`:
   `VOICE_WHISPER_MODEL=small`
   `VOICE_WHISPER_DEVICE=cpu`
   `VOICE_WHISPER_COMPUTE_TYPE=int8`
4. The first transcription downloads the selected Whisper model and can take longer.
5. Start FastAPI and Streamlit normally.

For a lower-memory computer, use `VOICE_WHISPER_MODEL=base`. For higher accuracy, use `medium` if the computer has enough RAM.
