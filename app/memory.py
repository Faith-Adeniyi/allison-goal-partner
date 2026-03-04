import json
import os
from datetime import datetime
from typing import List, Dict

class SessionMemory:
    """Manages conversational context with strict user and goal isolation."""
    
    def __init__(self, base_dir: str = "database/conversations"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _get_file_path(self, user_id: str, goal_id: str) -> str:
        """Generates an isolated file path for a specific user and goal."""
        user_dir = os.path.join(self.base_dir, user_id)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return os.path.join(user_dir, f"{goal_id}.json")

    def add_message(self, user_id: str, goal_id: str, role: str, message: str) -> bool:
        """
        Appends a timestamped message to the isolated conversation log.
        Matches the PRD schema: id, user_id, goal_id, message, role, timestamp.
        """
        file_path = self._get_file_path(user_id, goal_id)
        history = self._load_history(file_path)

        log_entry = {
            "id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "user_id": user_id,
            "goal_id": goal_id,
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        history.append(log_entry)

        with open(file_path, "w") as f:
            json.dump(history, f, indent=4)
        return True

    def get_context(self, user_id: str, goal_id: str) -> str:
        """Retrieves and formats the conversation history for the LLM context window."""
        file_path = self._get_file_path(user_id, goal_id)
        history = self._load_history(file_path)
        
        context = ""
        for entry in history:
            role_label = "User" if entry["role"] == "user" else "Allison"
            context += f"{role_label} ({entry['timestamp']}): {entry['message']}\n"
        return context

    def _load_history(self, file_path: str) -> List[Dict]:
        """Loads the conversation array from the local file system."""
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r") as f:
            return json.load(f)