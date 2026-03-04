# app/planner.py

from app.brain import GoalPlan

class AllisonPlanner:
    """
    Mode 1: The Goal Architect.
    Handles heavy computation to generate structured project plans.
    """
    def __init__(self, brain_client):
        self.brain = brain_client
        
        self.architect_prompt = (
            "You are Allison, a structured execution coach. "
            "You break goals into measurable milestones and actionable tasks. "
            "You focus on realism, discipline, and clarity. You avoid vague advice. "
            "You always provide structured output."
        )

    def generate_plan(self, context_history: str) -> GoalPlan:
        """
        Executes plan generation by ingesting validated conversational context 
        and enforcing strict JSON output compliance.
        """
        response = self.brain.client.models.generate_content(
            model=self.brain.model_id,
            contents=context_history,
            config={
                'system_instruction': self.architect_prompt,
                'response_mime_type': 'application/json',
                'response_schema': GoalPlan,
            }
        )
        return response.parsed