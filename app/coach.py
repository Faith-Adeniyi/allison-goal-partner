import os
import warnings
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

# Integrates the calendar MCP tool
from app.calendar_tool import create_calendar_event

load_dotenv()

genai.configure(api_key=os.environ.get("GENAI_API_KEY"))

class CoachMessagePayload(BaseModel):
    """Schema for the incoming conversational payload from the frontend Modal."""
    user_message: str
    energy_level: str = "normal"
    chat_history: list = Field(default_factory=list)

class ExecutionCoach:
    """
    Mode 2: The Execution Coach.
    Handles conversational computation for daily tracking, obstacle mitigation, 
    and agentic tool execution (Calendar Management).
    """
    def __init__(self, brain_client):
        self.brain = brain_client
        
        self.coach_prompt = (
            "You are Allison, an execution coach. "
            "Analyze the user's message and their goal progress. "
            "If they encountered blockers, provide a concise, actionable solution. "
            "If they succeeded, provide brief, professional reinforcement. "
            "NEVER shame or scold the user for missed tasks. "
            "Maintain a disciplined, supportive tone. Keep responses strictly under 3 sentences. "
            "CRITICAL CAPABILITY: You have access to the create_calendar_event tool. "
            "If the user asks to schedule a task or wants a reminder, you MUST use this tool to block out time on their calendar. "
            "Limit calendar events to a maximum of 3 per week to avoid clutter. "
            "Always confirm with the user once the event is successfully created."
            "PROACTIVE SCHEDULING: If the user states they plan to work on a task later, proactively ask if they would like you to block out time on their calendar. Keep the offer natural and brief."
        )

    def process_conversational_checkin(self, payload: CoachMessagePayload, plan_data: dict) -> str:
        """
        Evaluates the user's message against the overarching goal context, chat history,
        and dynamically triggers MCP tools if requested.
        """
        goal_summary = plan_data.get("goal_summary", "Unknown Goal")
        target_date = plan_data.get("target_date", "No date set")
        
        tasks_context = []
        for milestone in plan_data.get("milestones", []):
            for task in milestone.get("tasks", []):
                status = "Completed" if task.get("is_completed") == 1 else "Pending"
                tasks_context.append(f"- {task.get('title')} ({status})")
        
        context_string = "\n".join(tasks_context)

        context_string = "\n".join(tasks_context)
        
        # Give the AI a temporal anchor so it can calculate dates accurately
        current_time_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        system_instruction = f"""
        {self.coach_prompt}
        
        SYSTEM CONTEXT:
        Current Date and Time: {current_time_str}
        Timezone: Africa/Lagos
        
        GOAL CONTEXT:
        Goal: {goal_summary}
        Target Date: {target_date}
        User's Current Energy Level: {payload.energy_level}
        
        CURRENT PLAN STATUS:
        {context_string}
        """

        formatted_history = []
        for msg in payload.chat_history:
            if not msg.get("text") or "placeholder" in msg.get("text").lower():
                continue
            role = "model" if msg.get("sender") == "ai" else "user"
            formatted_history.append({"role": role, "parts": [msg.get("text")]})
            
        model = genai.GenerativeModel(
            model_name=self.brain.model_id, 
            system_instruction=system_instruction,
            tools=[create_calendar_event] # Injects the MCP tool into the AI's workbench
        )
        
        # Initializes chat with automatic function calling enabled via integer truthy value
        chat = model.start_chat(
            history=formatted_history, 
            enable_automatic_function_calling=bool(1) 
        )
        
        response = chat.send_message(payload.user_message)
        
        return response.text
