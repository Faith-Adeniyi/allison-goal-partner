import json
import os
from app.brain import AllisonBrain
from app.memory import SessionMemory
from app.planner import AllisonPlanner
from app.storage import PlanStorage

def run_integration_test():
    # Initialize components
    brain = AllisonBrain()
    memory = SessionMemory()
    planner = AllisonPlanner(brain)
    storage = PlanStorage()

    print("--- STARTING ALLISON LOGIC TEST ---")

    # STEP 1: Send a goal without a date
    print("\n[Step 1] Sending vague goal...")
    memory.add_message("user", "I want to start a fitness routine and lose 5kg.")
    resp1 = brain.get_response(memory.get_context())
    memory.add_message("assistant", resp1.text_reply)
    
    print(f"Allison: {resp1.text_reply}")
    print(f"Category: {resp1.goal_category} | Missing Date: {resp1.is_timeframe_missing}")

    # STEP 2: Send the Target Date
    print("\n[Step 2] Providing Target Date...")
    memory.add_message("user", "I want to achieve this in 3 months.")
    resp2 = brain.get_response(memory.get_context())
    memory.add_message("assistant", resp2.text_reply)

    print(f"Allison: {resp2.text_reply}")
    
    # STEP 3: Check Logic Gate & Generate Plan
    if not resp2.is_timeframe_missing:
        print("\n[Step 3] Logic Gate Passed. Generating Action Plan...")
        plan = planner.generate_plan(memory.get_context())
        
        # STEP 4: Test Storage
        path = storage.save_plan(plan)
        print(f"SUCCESS: Plan saved to {path}")
        
        # Verify file content
        with open(path, "r") as f:
            saved_data = json.load(f)
            print(f"Verified Milestone Count: {len(saved_data['milestones'])} weeks found.")
    else:
        print("\nFAILED: Logic gate did not detect the date.")

if __name__ == "__main__":
    run_integration_test()