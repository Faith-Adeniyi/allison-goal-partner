import os
from datetime import datetime

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.brain import AllisonBrain
from app.coach import CoachMessagePayload, ExecutionCoach
from app.db import get_db, init_db
from app.memory import SessionMemory
from app.models import User
from app.planner import AllisonPlanner
from app.reviewer import WeeklyReviewer
from app.schemas import (
    AuthResponse,
    ChatRequest,
    CheckinPayload,
    LoginRequest,
    SignUpRequest,
    UserOut,
)
from app.storage import PlanStorage

app = FastAPI(title="Allison: Goal Assistant API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:19006,http://127.0.0.1:19006,http://localhost:8081,http://127.0.0.1:8081,http://10.0.2.2:19006,http://10.0.2.2:8081",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
allison = AllisonBrain()
memory = SessionMemory()
planner = AllisonPlanner(allison)
storage = PlanStorage()
coach = ExecutionCoach(allison)
reviewer = WeeklyReviewer(allison)


def _serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        created_at=user.created_at,
    )


@app.get("/")
def read_root():
    return {"status": "online", "agent": "Allison"}


@app.post("/auth/signup", response_model=AuthResponse)
def sign_up(payload: SignUpRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.lower().strip()
    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists with this email.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=_serialize_user(user))


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=_serialize_user(user))


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


@app.post("/chat")
def chat_with_allison(
    user_input: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        user_id = str(current_user.id)
        memory.add_message(user_id, user_input.goal_id, "user", user_input.message)

        context = memory.get_context(user_id, user_input.goal_id)
        ai_data = allison.get_response(context)

        memory.add_message(user_id, user_input.goal_id, "assistant", ai_data.text_reply)

        action_plan = {}
        storage_path = "NOT_SAVED"

        if ai_data.has_active_goal and not ai_data.is_timeframe_missing and not ai_data.is_frequency_missing:
            plan_obj = planner.generate_plan(context)
            action_plan = plan_obj.model_dump()
            storage_path = storage.save_plan(plan_obj, owner_user_id=current_user.id)

        return {
            "reply": ai_data.text_reply,
            "category": ai_data.goal_category,
            "missing_date": ai_data.is_timeframe_missing,
            "missing_frequency": ai_data.is_frequency_missing,
            "action_plan": action_plan,
            "saved_at": storage_path,
        }
    except Exception as exc:
        print(f"SERVER ERROR: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/goals")
def get_active_goals(current_user: User = Depends(get_current_user)):
    try:
        plans = storage.get_all_plans(owner_user_id=current_user.id)
        return {"status": "success", "data": plans}
    except Exception as exc:
        print(f"DATABASE ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goals.")


@app.get("/goals/{plan_id}")
def get_goal_detail(plan_id: str, current_user: User = Depends(get_current_user)):
    try:
        plan_data = storage.load_plan(plan_id, owner_user_id=current_user.id)
        if not plan_data:
            raise HTTPException(status_code=404, detail="Goal plan not found.")
        return {"status": "success", "data": plan_data}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"FETCH ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goal details.")


@app.post("/goals/{plan_id}/coach")
def chat_with_coach(
    plan_id: str,
    payload: CoachMessagePayload,
    current_user: User = Depends(get_current_user),
):
    try:
        plan_data = storage.load_plan(plan_id, owner_user_id=current_user.id)
        if not plan_data:
            raise HTTPException(status_code=404, detail="Goal plan not found.")

        coach_response_text = coach.process_conversational_checkin(payload, plan_data)

        if "coach_history" not in plan_data:
            plan_data["coach_history"] = []

        timestamp = datetime.now().isoformat()
        plan_data["coach_history"].append(
            {"sender": "user", "text": payload.user_message, "timestamp": timestamp}
        )
        plan_data["coach_history"].append(
            {"sender": "ai", "text": coach_response_text, "timestamp": timestamp}
        )

        storage.save_plan_direct(plan_id, plan_data, owner_user_id=current_user.id)
        return {"status": "success", "plan_id": plan_id, "reply": coach_response_text}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"COACH ENDPOINT ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to process coach message.")


@app.post("/goals/{plan_id}/checkin")
def submit_daily_checkin(
    plan_id: str,
    payload: CheckinPayload,
    current_user: User = Depends(get_current_user),
):
    try:
        plan_data = storage.load_plan(plan_id, owner_user_id=current_user.id)
        if not plan_data:
            raise HTTPException(status_code=404, detail="Goal plan not found.")

        if "checkins" not in plan_data or not isinstance(plan_data["checkins"], list):
            plan_data["checkins"] = []

        checkin_entry = {
            "date": datetime.now().date().isoformat(),
            "worked_today": payload.worked_today,
            "notes": payload.notes,
            "blockers": payload.blockers,
            "energy_level": payload.energy_level,
            "timestamp": datetime.now().isoformat(),
        }
        plan_data["checkins"].append(checkin_entry)

        storage.save_plan_direct(plan_id, plan_data, owner_user_id=current_user.id)
        return {"status": "success", "plan_id": plan_id, "checkin": checkin_entry}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"CHECK-IN ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to submit daily check-in.")


@app.post("/goals/{plan_id}/weekly-review")
def trigger_weekly_review(plan_id: str, current_user: User = Depends(get_current_user)):
    try:
        plan_data = storage.load_plan(plan_id, owner_user_id=current_user.id)
        if not plan_data:
            raise HTTPException(status_code=404, detail="Goal plan not found.")

        goal_summary = plan_data.get("goal_summary", "Active personal development goal.")
        checkins = plan_data.get("checkins", [])

        total_tasks = 0
        completed_tasks = 0
        for milestone in plan_data.get("milestones", []):
            tasks = milestone.get("tasks", [])
            total_tasks += len(tasks)
            completed_tasks += sum(1 for task in tasks if task.get("is_completed", 0) == 1)

        review_report = reviewer.generate_review(
            goal_summary=goal_summary,
            checkin_logs=checkins,
            tasks_completed=completed_tasks,
            tasks_total=total_tasks,
        )

        return {
            "status": "success",
            "plan_id": plan_id,
            "review_report": review_report.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"REVIEW ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate weekly review.")


@app.patch("/goals/{plan_id}/check/{milestone_id}/{task_id}")
def toggle_task(
    plan_id: str,
    milestone_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    try:
        plan_data = storage.load_plan(plan_id, owner_user_id=current_user.id)
        if plan_data is None:
            raise HTTPException(status_code=404, detail="Goal plan not found.")

        ordered_tasks = []
        target_index = -1
        target_task = {}

        for milestone in sorted(plan_data.get("milestones", []), key=lambda item: item.get("id", 0)):
            for task in sorted(milestone.get("tasks", []), key=lambda item: item.get("id", 0)):
                ordered_tasks.append(task)
                if milestone.get("id") == milestone_id and task.get("id") == task_id:
                    target_task = task
                    target_index = len(ordered_tasks) - 1

        if target_index == -1:
            raise HTTPException(status_code=404, detail="Task not found in specified milestone.")

        is_currently_completed = target_task.get("is_completed", 0)

        if is_currently_completed == 0:
            for idx in range(target_index):
                if ordered_tasks[idx].get("is_completed", 0) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Preceding tasks must be completed first.",
                    )

        if is_currently_completed == 1:
            for idx in range(target_index + 1, len(ordered_tasks)):
                if ordered_tasks[idx].get("is_completed", 0) == 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot uncheck task while subsequent tasks are completed.",
                    )

        target_task["is_completed"] = 0 if is_currently_completed == 1 else 1

        for milestone in plan_data.get("milestones", []):
            tasks_in_milestone = milestone.get("tasks", [])
            if tasks_in_milestone:
                completed_in_milestone = sum(
                    1 for task in tasks_in_milestone if task.get("is_completed", 0) == 1
                )
                milestone["is_completed"] = 1 if completed_in_milestone == len(tasks_in_milestone) else 0

        storage.save_plan_direct(plan_id, plan_data, owner_user_id=current_user.id)

        total_steps = len(ordered_tasks)
        completed_steps = sum(1 for task in ordered_tasks if task.get("is_completed", 0) == 1)
        new_progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0

        return {
            "status": "success",
            "plan_id": plan_id,
            "milestone_id": milestone_id,
            "task_id": task_id,
            "new_progress": new_progress,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"UPDATE ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update task status.")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=True,
    )
