# 🏃 AI Endurance Training Coach

A modular, **100% free** AI training coach powered by **Garmin Connect** biometric data, **MongoDB Atlas**, **Streamlit**, and **Google Gemini**.

---

## 🏗️ Architecture

```
training-coach/
│
├── .github/workflows/
│   └── daily_sync.yml        # Automates daily morning data sync (Free on GitHub Actions)
│
├── sync/                     # INGESTION LAYER (Garmin -> MongoDB)
│   ├── garmin_auth.py        # Centralized login & session token caching
│   ├── sync_activities.py    # Pulls runs, laps, paces, HR zones, elevation
│   ├── sync_recovery.py      # Pulls sleep scores, overnight HRV, resting HR
│   └── sync_all.py           # Pipeline runner to sync everything
│
├── db/                       # DATA ACCESS LAYER (MongoDB repositories)
│   ├── client.py             # Shared Mongo connection
│   ├── activities_repo.py    # Upsert and query running workouts
│   ├── recovery_repo.py      # Upsert and query daily sleep & HRV
│   ├── conversations_repo.py # Persistent chat history
│   └── profile_repo.py       # Goals, race targets, and injury tracking
│
├── coach/                    # AI REASONING LAYER
│   ├── prompts.py            # Formats biometric metrics into coach instructions
│   └── engine.py             # Context assembler & Gemini API client with congestion fallback
│
├── app.py                    # PRESENTATION LAYER (Streamlit Web UI)
├── requirements.txt          # Python dependencies
└── .env                      # Local secret keys
```

---

## 🚀 Quickstart

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```env
GARMIN_EMAIL=your_garmin_email
GARMIN_PASSWORD=your_garmin_password
MONGO_URI=your_mongodb_connection_string
GEMINI_API_KEY=your_free_gemini_api_key
```
> **Get Gemini API Key for Free**: Visit [Google AI Studio](https://aistudio.google.com/) and create a free API key (no credit card required).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Data Sync (Garmin -> MongoDB)
You can sync activities and recovery separately or all at once:
```bash
# Sync both activities and recovery
python sync/sync_all.py

# Or sync individually:
python sync/sync_activities.py
python sync/sync_recovery.py
```

### 4. Launch the AI Coach Web UI
```bash
streamlit run app.py
```
The app requires a login. For local use, create `.streamlit/secrets.toml` (this file
is ignored by Git) and add:
```toml
[auth]
username = "your_username"
password = "a_long_unique_password"
```

Add your `MONGO_URI` and `GEMINI_API_KEY` to the same file as top-level settings,
or keep using your `.env` file. Environment variables take precedence over Streamlit
secrets.

The coach tries the configured `GEMINI_MODEL` first (default: `gemini-4-hydrogen`). If
that model is congested, it immediately tries `gemini-3.8-flash`; the UI displays the
model used for each response.

---

## ☁️ 100% Free Cloud Deployment

### 1. Free Daily Background Sync (GitHub Actions)
- Push your project to a **private GitHub repository**.
- Go to **Settings > Secrets and variables > Actions > New repository secret**.
- Add `GARMIN_EMAIL`, `GARMIN_PASSWORD`, and `MONGO_URI`.
- The `.github/workflows/daily_sync.yml` workflow will automatically run every morning at 06:00 UTC and populate your MongoDB.

### 2. Free 24/7 Web App (Streamlit Community Cloud)
- Go to [share.streamlit.io](https://share.streamlit.io).
- Connect your GitHub repo and select `app.py`.
- In **App Settings > Secrets**, paste your `.env` variables:
  ```toml
  MONGO_URI = "mongodb+srv://..."
  GEMINI_API_KEY = "AIzaSy..."

  [auth]
  username = "your_username"
  password = "a_long_unique_password"
  ```
- Keep `GARMIN_EMAIL` and `GARMIN_PASSWORD` only in GitHub Actions secrets for the
  daily sync; the Streamlit app does not need them.
- Use a unique, strong password. The app checks it on every new Streamlit session;
  selecting **Log out** ends the current session.
- Deploy! You will have a permanent, free URL to talk to your coach on your phone or laptop.
