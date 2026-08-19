# Sikkim Tourist AI — Travel Assistant & Knowledge System

## Stack
Python + Streamlit + SQLite + Requests + BeautifulSoup, with optional Ollama/Qwen enhancement.

## Install on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ollama is optional. When it is unavailable, the public assistant formats answers
directly from approved knowledge-base records. For local AI-enhanced responses,
install Ollama from:
https://ollama.com/download/windows

Then:
```powershell
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

Copy `.env.example` to `.env`.

Initialize database:
```powershell
python -m database.db
```

Run dashboard:
```powershell
streamlit run streamlit_app.py
```

Public website: `http://localhost:8501/`

Protected admin console: `http://localhost:8501/admin`

Or collect from CLI:
```powershell
python -m agent.collector https://example.com
```

The crawler stays on the same domain and respects a maximum page count. AI records are always `pending_review` until manually approved.

For production, verify permits, road conditions, prices, weather, restrictions, opening hours and emergency information against current authoritative sources before approval.

## Free web deployment

The project is prepared for Streamlit Community Cloud:

1. Push this repository to GitHub.
2. Sign in at [share.streamlit.io](https://share.streamlit.io/), choose **Create app**,
   and select `streamlit_app.py` on the `main` branch.
3. In **Advanced settings → Secrets**, add:

   ```toml
   ADMIN_PASSWORD = "use-a-long-random-password"
   ```

4. Deploy the app. The public landing page opens at the root URL and the protected
   console is available at `/admin`.

Streamlit Community Cloud local storage is not guaranteed to persist. The bundled
approved SQLite knowledge base is suitable for reading and demonstrations, but use
a hosted database before relying on cloud-side admin edits as permanent records.
