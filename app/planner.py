from pydantic import BaseModel
from typing import List

class WeeklyTask(BaseModel):
    week_number: int
    task_description: str
    focus_area: str

class GoalPlan(BaseModel):
    goal_summary: str
    target_date: str
    milestones: List[WeeklyTask]

# This class handles the logic of generating the structured breakdown
class AllisonPlanner:
    def __init__(self, brain_instance):
        self.brain = brain_instance

    def generate_plan(self, history):
        # Create a copy of history to avoid modifying the primary chat session
        temp_history = list(history)
        
        planning_prompt = (
            "Based on our conversation, create a step-by-step weekly action plan "
            "to reach the target date. Break it down into clear, manageable weeks."
        )
        
        # Append the planning request using the multi-part content format
        temp_history.append({
            "role": "user", 
            "parts": [{"text": planning_prompt}]
        })
        
        # Request the structured plan from the brain
        return self.brain.get_structured_plan(temp_history)