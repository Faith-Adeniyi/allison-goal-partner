import os
import sys

# Allow running from repo root without installing as a package.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.storage import PlanStorage


def main():
    storage = PlanStorage()
    plan_id = "plan_20260305_162927"
    owner_user_id = 1

    before = storage.get_streak(plan_id, owner_user_id=owner_user_id)
    print("BEFORE:", before)

    storage.apply_task_completion_activity(plan_id, owner_user_id=owner_user_id)

    after = storage.get_streak(plan_id, owner_user_id=owner_user_id)
    print("AFTER:", after)


if __name__ == "__main__":
    main()
