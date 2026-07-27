# Phase 6 Provider Fix

Copy these files into the root of your existing MediSimplify AI repository and replace files when prompted.

## Fixes included

- Accepts valid JSON wrapped in Markdown or surrounded by short explanatory text.
- Keeps strict rejection for genuinely truncated or invalid JSON.
- Increases Phase 5 structured medical explanation output limit from 4096 to 8192 tokens.
- Disables Ollama fallback unless `OLLAMA_ENABLED=true` is explicitly configured.
- Adds parser regression tests.

## Environment setting

Keep this in `backend/.env` when Ollama is not installed/running:

```env
OLLAMA_ENABLED=false
```

To use Ollama later:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Test

From `backend`:

```powershell
python -m pytest -q
```

Expected result for this patched project: `39 passed`.
