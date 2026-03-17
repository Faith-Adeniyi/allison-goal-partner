# app/brain.py

import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from typing import List
from app.utils.persona import BASE_SYSTEM_PROMPT
from app.utils.prompts import ALLISON_SYSTEM_PROMPT
from app.schemas import IntentRouter

load_dotenv()

class TaskItem(BaseModel):
    """Schema representing discrete, actionable steps within a milestone."""
    id: int = Field(description="Sequential identifier for the task.")
    title: str = Field(description="Short, actionable task description.")
    is_completed: int = 0

class MilestoneItem(BaseModel):
    """Schema representing a major project phase containing nested tasks."""
    id: int = Field(description="Sequential identifier for the milestone.")
    title: str = Field(description="Title of the milestone phase.")
    tasks: List[TaskItem]
    is_completed: int = 0

class GoalPlan(BaseModel):
    """Comprehensive structure of a user goal per the PRD specifications."""
    goal_summary: str
    target_date: str
    weekly_structure_suggestion: str = Field(description="Recommended weekly execution strategy.")
    milestones: List[MilestoneItem]
    
    @property
    def progress_percentage(self):
        """Calculates the integer completion percentage based on total tasks."""
        if not self.milestones:
            return 0
            
        total_tasks = 0
        completed_tasks = 0
        
        for milestone in self.milestones:
            for task in milestone.tasks:
                total_tasks += 1
                if task.is_completed:
                    completed_tasks += 1
                    
        return int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

class AllisonResponse(BaseModel):
    """Schema for intent classification and standard conversational output."""
    text_reply: str
    goal_category: str
    has_active_goal: bool
    is_timeframe_missing: bool
    is_frequency_missing: bool 
    target_date: str

class AllisonBrain:
    """Core execution engine for the AI agent."""
    def __init__(self):
        self.api_key = os.getenv("GENAI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-1.5-flash" 

    def get_response(self, chat_history):
        """Processes conversational input against the core persona matrix with strict two-phase commitment protocol."""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=chat_history,
            config={
                'system_instruction': ALLISON_SYSTEM_PROMPT,
                'response_mime_type': 'application/json',
                'response_schema': IntentRouter,
            }
        )
        return response.parsed
