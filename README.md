# EuroGoal Predictor ⚽ (Brighton/Starlizard Quant Edition)

An interactive football match prediction & simulation system: xG-Dixon-Coles
bivariate Poisson models, Elo ratings, a fully vectorised Monte-Carlo engine,
and a complete **2026 FIFA World Cup** module. A FastAPI backend serves a React
(Vite) single-page frontend.

## Features
- **Match simulator** — Dixon-Coles expected goals fed into a minute-by-minute
  Monte-Carlo, with human-in-the-loop tactical sliders (stamina/fatigue,
  park-the-bus, tactical conservatism, attack/defense tweaks).
- **Leagues** (PL, La Liga, Bundesliga, Serie A, Ligue 1, UCL) — standings,
  upcoming-match predictions, betting-odds value bets, head-to-head, lineups.
- **World Cup 2026** — real schedule & live results (kick-offs in Central
  European time), per-match **locked pre-match predictions vs. actual results**
  with an accuracy/Brier scoreboard, full group-stage Monte-Carlo, knockout
  bracket, and championship probabilities. National-team strengths are
  Elo-seeded and **self-calibrate from real results** as the tournament runs.

## Tech stack
**Backend:** FastAPI · NumPy · SciPy · Pandas · SQLite · httpx
**Frontend:** React · Vite · lucide-react · glassmorphic CSS

## Run locally
Requires **Python 3.12+** and **Node 18+**.

```bash
# 1) API keys (optional — see table below)
cp .env.example .env        # then fill in any keys you have

# 2) Build the frontend
cd frontend && npm install && npm run build && cd ..

# 3) Run the backend (it also serves the built frontend)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```
On Windows you can instead just run `./run.ps1` (builds the frontend if needed
and starts the server).

## Environment variables
All optional — the app degrades gracefully when a key is missing.

| Variable | Powers | Get a free key |
|---|---|---|
| `FOOTBALL_DATA_API_KEY` | League results + **World Cup** schedule/results | https://www.football-data.org/ |
| `THE_ODDS_API_KEY` | Betting odds + value bets | https://the-odds-api.com/ |
| `API_FOOTBALL_KEY` | Head-to-head + lineups | https://www.api-football.com/ |

## Deploy (Render · Docker)
This repo ships a multi-stage `Dockerfile` (builds the frontend, then serves it
from FastAPI) and a `render.yaml` blueprint, so deployment is one service.

1. Push to GitHub.
2. On [Render](https://render.com): **New → Blueprint** and pick this repo
   (or **New → Web Service → Docker** if you prefer manual setup).
3. Set the three environment variables above — Render prompts for them and
   stores them as secrets; they are **never** committed to the repo.
4. Deploy. Render builds the image and runs `uvicorn` on `$PORT`; the health
   check hits `/api/health`.

**Notes on the free tier:** the service sleeps when idle (cold start ~30s) and
uses an ephemeral filesystem, so the local SQLite DB resets on each redeploy.
The World Cup module re-fetches live data on demand, so it is unaffected;
attach a persistent disk if you want durable fitted league models.

## Credits
Quantitative backend models by **Claude Opus**; interactive frontend by
**Gemini**.
