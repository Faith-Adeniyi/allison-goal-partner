from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.brain import AllisonBrain
from app.memory import SessionMemory
from app.planner import AllisonPlanner
from app.storage import PlanStorage

# Core application setup
app = FastAPI(title="Allison: Goal Partner API")

# Logic component initialization
allison = AllisonBrain()
memory = SessionMemory()
planner = AllisonPlanner(allison)
storage = PlanStorage()

class UserMessage(BaseModel):
    message: str

@app.post("/chat")
def chat_with_allison(user_input: UserMessage):
    try:
        # Append the user's message to the ongoing session history
        memory.add_message("user", user_input.message)
        
        # Request a structured response from the brain using the full context
        ai_data = allison.get_response(memory.get_context())
        
        # Record Allison's response in history to maintain continuity
        # Note: 'assistant' is automatically mapped to 'model' in SessionMemory
        memory.add_message("assistant", ai_data.text_reply)
        
        action_plan = None
        storage_path = "NOT_SAVED"

        # Logic Gate: Proceed to planning only when the target date is confirmed
        if not ai_data.is_timeframe_missing:
            action_plan = planner.generate_plan(memory.get_context())
            # Persist the finalized plan to a local JSON file
            storage_path = storage.save_plan(action_plan)
        
        return {
            "reply": ai_data.text_reply,
            "category": ai_data.goal_category,
            "missing_date": ai_data.is_timeframe_missing,
            "action_plan": action_plan,
            "saved_at": storage_path
        }
    except Exception as e:
        # Generic error handling to prevent server crashes
        raise HTTPException(status_code=500, detail=str(e))