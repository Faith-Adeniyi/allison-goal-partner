import json
import os
from datetime import datetime


class PlanStorage:
    def __init__(self):
        self.base_dir = "saved_plans"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _file_path(self, plan_id: str) -> str:
        return os.path.join(self.base_dir, f"{plan_id}.json")

    @staticmethod
    def _owner_matches(plan_dict: dict, owner_user_id: int | None) -> bool:
        if owner_user_id is None:
            return True
        current_owner = plan_dict.get("owner_user_id")
        return current_owner is not None and str(current_owner) == str(owner_user_id)

    def _claim_if_unowned(self, plan_id: str, plan_dict: dict, owner_user_id: int | None):
        if owner_user_id is None:
            return plan_dict

        if plan_dict.get("owner_user_id") is None:
            plan_dict["owner_user_id"] = owner_user_id
            self.save_plan_direct(plan_id, plan_dict, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan_dict

    def save_plan(self, plan_obj, owner_user_id: int | None = None):
        plan_dict = plan_obj.model_dump() if hasattr(plan_obj, "model_dump") else dict(plan_obj)
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        plan_dict["plan_id"] = plan_id
        if owner_user_id is not None:
            plan_dict["owner_user_id"] = owner_user_id

        file_path = self._file_path(plan_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=4)

        return plan_id

    def load_plan(self, plan_id: str, owner_user_id: int | None = None):
        file_path = self._file_path(plan_id)
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data = self._claim_if_unowned(plan_id, data, owner_user_id)
        if not self._owner_matches(data, owner_user_id):
            return None
        return data

    def save_plan_direct(
        self,
        plan_id: str,
        plan_dict: dict,
        owner_user_id: int | None = None,
        bypass_owner_check: bool = False,
    ):
        if not bypass_owner_check and owner_user_id is not None:
            current = self.load_plan(plan_id)
            if current is None:
                return False
            if not self._owner_matches(current, owner_user_id):
                return False

        file_path = self._file_path(plan_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=4)
        return True

    def get_all_plans(self, owner_user_id: int | None = None):
        plans = []

        for filename in os.listdir(self.base_dir):
            if not filename.endswith(".json"):
                continue

            fallback_id = filename[:-5]
            plan_data = self.load_plan(fallback_id, owner_user_id=owner_user_id)
            if not plan_data:
                continue

            actual_plan_id = plan_data.get("plan_id", fallback_id)
            milestones = plan_data.get("milestones", [])
            total_tasks = 0
            completed_tasks = 0

            for milestone in milestones:
                tasks = milestone.get("tasks", [])
                total_tasks += len(tasks)
                completed_tasks += sum(1 for task in tasks if task.get("is_completed", 0) == 1)

            progress = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
            plans.append(
                {
                    "plan_id": actual_plan_id,
                    "goal_summary": plan_data.get("goal_summary", "Untitled Goal"),
                    "category": plan_data.get("category", "Uncategorized"),
                    "progress": progress,
                }
            )

        return plans
