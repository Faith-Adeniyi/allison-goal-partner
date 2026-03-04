# Allison: Agentic Goal Partner

Allison is a sophisticated AI assistant designed to be a "Goal Partner" rather than a simple tracker. Built with a focus on **Agentic Workflows** and the **Model Context Protocol (MCP)**, Allison helps users define, track, and memorize their paths to success.

## Core Features
* **Intent Classification:** Dynamically categorizes goals (Career, Finance, Health, etc.).
* **Adaptive Timelines:** Generates flexible action checklists that adjust to user progress.
* **Memory Reinforcement:** Utilizes the 'Clock Rail' and 'Alphabetizing' techniques to help users internalize their plans.
* **Proactive Integration:** Connects to Calendar and Alarm systems for timely nudges.

## Tech Stack
* **Backend:** Python, FastAPI
* **AI Engine:** Google Gemini (Generative AI)
* **Data Validation:** Pydantic
* **Memory:** Vector Context & Spaced Repetition Logic

## Local Run
```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Auth + API Contract
All goal/chat endpoints are JWT-protected.

Auth routes:
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`

Protected routes:
- `POST /chat`
- `GET /goals`
- `GET /goals/{plan_id}`
- `POST /goals/{plan_id}/coach`
- `POST /goals/{plan_id}/checkin`
- `PATCH /goals/{plan_id}/check/{milestone_id}/{task_id}`
- `POST /goals/{plan_id}/weekly-review`
