import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import List
from app.utils.prompts import ALLISON_SYSTEM_PROMPT

load_dotenv()

# Schema for weekly tasks
class WeeklyTask(BaseModel):
    week_number: int
    task_description: str
    focus_area: str

# Schema for the full plan
class GoalPlan(BaseModel):
    goal_summary: str
    target_date: str
    milestones: List[WeeklyTask]

# Schema for standard conversation
class AllisonResponse(BaseModel):
    text_reply: str
    goal_category: str
    is_timeframe_missing: bool
    target_date: str 

class AllisonBrain:
    def __init__(self):
        self.api_key = os.getenv("GENAI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-2.5-flash'

    def get_response(self, chat_history):
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=chat_history,
            config={
                'system_instruction': ALLISON_SYSTEM_PROMPT,
                'response_mime_type': 'application/json',
                'response_schema': AllisonResponse,
            }
        )
        return response.parsed

    def get_structured_plan(self, chat_history):
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=chat_history,
            config={
                'system_instruction': "You are an expert project planner. Create a high-impact weekly breakdown for the goal discussed.",
                'response_mime_type': 'application/json',
                'response_schema': GoalPlan,
            }
        )
        return response.parsed