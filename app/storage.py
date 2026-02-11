import json
from pathlib import Path
from app.utils.helpers import sanitize_filename

class PlanStorage:
    def __init__(self, storage_dir="saved_plans"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def save_plan(self, plan_data):
        # Use the helper to create a safe filename
        safe_name = sanitize_filename(plan_data.goal_summary[:30])
        filename = f"{safe_name}.json"
        file_path = self.storage_dir / filename
        
        with open(file_path, "w") as f:
            json.dump(plan_data.model_dump(), f, indent=4)
        
        return str(file_path)