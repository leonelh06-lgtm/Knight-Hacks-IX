# KnightHacks FastAPI backend

This is the initial Python backend for KnightHacks IX. It provides health and
voice-integration status endpoints and is intentionally not connected to
ElevenLabs. It does not generate audio, make ElevenLabs API requests, or require
ElevenLabs credentials to start.

## Requirements

- Python 3.12 or newer
- `pip`

## Set up a virtual environment

From the repository's `backend/` directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Configure environment variables

Copy the example file and edit it as needed:

```bash
cp .env.example .env
```

The ElevenLabs key and voice ID may remain blank. They are optional and are not
used to make network requests. `CORS_ORIGINS` is a JSON array of exact origins;
the defaults allow common local frontend origins on ports 3000 and 5173. To
allow a different local frontend, set the array explicitly, for example:

```dotenv
CORS_ORIGINS=["http://localhost:4200"]
```

Do not commit `.env` or put real API keys in source control. The backend's
`.gitignore` excludes `.env` and `.venv/`.

## Start the server

Run from the `backend/` directory with the virtual environment active:

```bash
uvicorn app.main:app --reload --port 8000
```

The server listens at `http://127.0.0.1:8000`. Interactive Swagger UI is
available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs);
ReDoc is available at `/redoc`.

## Endpoints

### `GET /api/health`

Returns `{"status":"ok","service":"knighthacks-backend"}`.

### `GET /api/voice/status`

Without an API key and voice ID, returns
`{"configured":false,"message":"ElevenLabs integration not configured yet"}`.
If both settings are supplied, the response reports that credentials are
configured while making clear that integration is not implemented. No
credentials are returned in API responses or logged by this service.

## Run tests

From the `backend/` directory:

```bash
pytest
```

Tests use FastAPI's in-process test client and verify startup without
ElevenLabs credentials, health and voice-status responses, and that the voice
status endpoint makes no asynchronous HTTP requests.

## Future ElevenLabs work

The service module is a placeholder only. API client lifecycle, request and
response schemas, asynchronous API calls, audio generation, error mapping,
voice selection, and secret provisioning remain to be designed and implemented
later. HTTPX is included for that future work but is not currently used for
outbound requests.
