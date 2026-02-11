# Manage conversation history to provide context for the AI
class SessionMemory:
    def __init__(self):
        # Stores the list of previous messages in the 2026 SDK format
        self.history = []

    def add_message(self, role: str, text: str):
        # Map 'assistant' to 'model' to comply with Google GenAI SDK requirements
        valid_role = "model" if role == "assistant" else role
        
        # Appends a new interaction using the required 'parts' structure
        self.history.append({
            "role": valid_role, 
            "parts": [{"text": text}]
        })

    def get_context(self):
        # Returns the full history for the AI to process
        return self.history

    def clear(self):
        # Resets the memory for a new goal session
        self.history = []