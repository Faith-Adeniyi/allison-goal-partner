from app.brain import AllisonBrain

# Initialize the brain
allison = AllisonBrain()

# Ask the same question as before
print("--- Testing Persona ---")
print(allison.get_response("Hello, who are you and can you help me?"))