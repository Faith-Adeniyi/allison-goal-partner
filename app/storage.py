import json
import os
from datetime import date, datetime, timedelta, timezone


def _utc_today() -> date:
    """
    Use UTC day boundaries so streak "day" math is consistent regardless of server timezone.
    """
    return datetime.now(timezone.utc).date()


def _today_iso() -> str:
    return _utc_today().isoformat()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def _week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _coerce_plan_meta(plan: dict) -> dict:
    """
    Ensures required meta keys exist for new features without breaking old saved plans.
    This mutates the plan dict in-place and returns it.
    """
    plan.setdefault("meta", {})
    plan["meta"].setdefault("target_date", plan.get("target_date"))
    plan.setdefault("streak", {})
    plan["streak"].setdefault("current_streak", 0)
    plan["streak"].setdefault("longest_streak", 0)
    plan["streak"].setdefault("last_active_date", None)
    plan["streak"].setdefault("freeze_week_key", None)
    plan["streak"].setdefault("freeze_available", 1)
    return plan


def _reset_streak(plan: dict) -> None:
    plan["streak"] = {
        "current_streak": 0,
        "longest_streak": 0,
        "last_active_date": None,
        "freeze_week_key": None,
        "freeze_available": 1,
    }


def _parse_iso_date_or_datetime(value: str | None) -> date | None:
    if not value:
        return None
    parsed = _parse_iso_date(str(value))
    if parsed:
        return parsed
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def _backfill_streak_from_checkins(plan: dict) -> None:
    checkins = plan.get("checkins") or []
    if not checkins:
        return

    _coerce_plan_meta(plan)
    streak = plan.get("streak") or {}
    if streak.get("last_active_date") or int(streak.get("current_streak", 0)) > 0:
        return

    worked_dates = []
    for entry in checkins:
        if not entry or entry.get("worked_today") is not True:
            continue
        raw_date = entry.get("date") or entry.get("timestamp")
        parsed = _parse_iso_date_or_datetime(raw_date)
        if parsed:
            worked_dates.append(parsed)

    if not worked_dates:
        return

    _reset_streak(plan)
    for activity_date in sorted(set(worked_dates)):
        _update_streak_for_activity(plan, activity_date)


def _assign_due_dates(plan: dict) -> None:
    """
    Auto-assign due dates for milestones and tasks when a target_date exists.
    Strategy:
      - Split remaining days evenly across milestones.
      - Split each milestone window evenly across its tasks.
    Dates are stored as YYYY-MM-DD strings in `milestone.due_date` and `task.due_date`.
    """
    milestones = plan.get("milestones") or []
    if not milestones:
        return

    target = _parse_iso_date(plan.get("meta", {}).get("target_date") or plan.get("target_date"))
    if not target:
        return

    start = _utc_today()
    if target < start:
        target = start

    total_days = max(0, (target - start).days)
    milestone_count = max(1, len(milestones))
    per_milestone = max(1, total_days // milestone_count) if total_days else 1

    current_start = start
    for idx, milestone in enumerate(sorted(milestones, key=lambda m: m.get("id", 0))):
        window_end = target if idx == milestone_count - 1 else min(target, current_start + timedelta(days=per_milestone))
        milestone.setdefault("due_date", window_end.isoformat())

        tasks = milestone.get("tasks") or []
        if not tasks:
            current_start = window_end
            continue

        task_count = max(1, len(tasks))
        window_days = max(0, (window_end - current_start).days)
        per_task = max(1, window_days // task_count) if window_days else 1

        t_start = current_start
        for t_idx, task in enumerate(sorted(tasks, key=lambda t: t.get("id", 0))):
            t_due = window_end if t_idx == task_count - 1 else min(window_end, t_start + timedelta(days=per_task))
            task.setdefault("due_date", t_due.isoformat())
            t_start = t_due

        current_start = window_end


def _update_streak_for_activity(plan: dict, activity_date: date) -> None:
    """
    Updates streak when user completes at least one task on `activity_date`.
    Includes 1 freeze/week:
      - If user misses exactly 1 day, they can consume freeze for that ISO week.
    """
    _coerce_plan_meta(plan)
    streak = plan["streak"]

    last_active = _parse_iso_date(streak.get("last_active_date"))
    today = activity_date
    current_week = _week_key(today)

    # reset weekly freeze allowance when week changes
    if streak.get("freeze_week_key") != current_week:
        streak["freeze_week_key"] = current_week
        streak["freeze_available"] = 1

    if last_active is None:
        streak["current_streak"] = 1
    else:
        delta = (today - last_active).days
        if delta == 0:
            # already counted today
            return
        if delta == 1:
            streak["current_streak"] = int(streak.get("current_streak", 0)) + 1
        elif delta == 2 and int(streak.get("freeze_available", 0)) > 0:
            # missed one day, use freeze
            streak["freeze_available"] = 0
            streak["current_streak"] = int(streak.get("current_streak", 0)) + 1
        else:
            streak["current_streak"] = 1

    streak["last_active_date"] = today.isoformat()
    streak["longest_streak"] = max(int(streak.get("longest_streak", 0)), int(streak.get("current_streak", 0)))


def _reindex_items(items: list[dict], id_key: str = "id") -> None:
    """Force 1..N integer ids to match current list order."""
    for idx, item in enumerate(items, start=1):
        item[id_key] = idx


def _refresh_completion_flags(plan: dict) -> None:
    """Recompute milestone is_completed flags based on tasks."""
    for milestone in plan.get("milestones") or []:
        tasks = milestone.get("tasks") or []
        if tasks and all((t.get("is_completed", 0) == 1) for t in tasks):
            milestone["is_completed"] = 1
        else:
            milestone["is_completed"] = 0


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

        _coerce_plan_meta(data)
        _backfill_streak_from_checkins(data)
        _assign_due_dates(data)
        # Persist normalized fields so all clients see consistent shape
        self.save_plan_direct(plan_id, data, owner_user_id=owner_user_id, bypass_owner_check=True)

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

    def delete_plan(self, plan_id: str, owner_user_id: int | None = None) -> bool:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return False

        file_path = self._file_path(plan_id)
        if not os.path.exists(file_path):
            return False

        os.remove(file_path)
        return True

    def get_streak(self, plan_id: str, owner_user_id: int | None = None) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None
        _coerce_plan_meta(plan)
        return plan.get("streak") or {}

    def update_target_date(self, plan_id: str, target_date: str | None, owner_user_id: int | None = None) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        _coerce_plan_meta(plan)
        plan["meta"]["target_date"] = target_date
        plan["target_date"] = target_date  # keep legacy key in sync
        _assign_due_dates(plan)

        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

    def add_task(
        self,
        plan_id: str,
        milestone_id: int,
        title: str,
        due_date: str | None = None,
        owner_user_id: int | None = None,
    ) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        milestones = plan.get("milestones") or []
        milestone = next((m for m in milestones if int(m.get("id", 0)) == int(milestone_id)), None)
        if milestone is None:
            return None

        tasks = milestone.setdefault("tasks", [])
        next_id = (max([int(t.get("id", 0)) for t in tasks] or [0]) + 1) if tasks else 1

        task = {"id": next_id, "title": title, "is_completed": 0}
        if due_date is not None:
            task["due_date"] = due_date
        tasks.append(task)

        _reindex_items(tasks, "id")
        _refresh_completion_flags(plan)
        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

    def update_task(
        self,
        plan_id: str,
        milestone_id: int,
        task_id: int,
        title: str | None = None,
        due_date: str | None = None,
        owner_user_id: int | None = None,
    ) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        milestone = next(
            (m for m in (plan.get("milestones") or []) if int(m.get("id", 0)) == int(milestone_id)),
            None,
        )
        if milestone is None:
            return None

        task = next((t for t in (milestone.get("tasks") or []) if int(t.get("id", 0)) == int(task_id)), None)
        if task is None:
            return None

        if title is not None:
            task["title"] = title
        if due_date is not None:
            task["due_date"] = due_date

        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

    def delete_task(
        self,
        plan_id: str,
        milestone_id: int,
        task_id: int,
        owner_user_id: int | None = None,
    ) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        milestone = next(
            (m for m in (plan.get("milestones") or []) if int(m.get("id", 0)) == int(milestone_id)),
            None,
        )
        if milestone is None:
            return None

        tasks = milestone.get("tasks") or []
        before = len(tasks)
        tasks = [t for t in tasks if int(t.get("id", 0)) != int(task_id)]
        if len(tasks) == before:
            return None

        milestone["tasks"] = tasks
        _reindex_items(tasks, "id")
        _refresh_completion_flags(plan)

        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

    def reorder_tasks(
        self,
        plan_id: str,
        milestone_id: int,
        ordered_task_ids: list[int],
        owner_user_id: int | None = None,
    ) -> dict | None:
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        milestone = next(
            (m for m in (plan.get("milestones") or []) if int(m.get("id", 0)) == int(milestone_id)),
            None,
        )
        if milestone is None:
            return None

        tasks = (milestone.get("tasks") or []).copy()
        task_by_id = {int(t.get("id", 0)): t for t in tasks}

        # Validate ids match current tasks
        current_ids = sorted(task_by_id.keys())
        incoming_ids = sorted([int(x) for x in ordered_task_ids])
        if current_ids != incoming_ids:
            return None

        milestone["tasks"] = [task_by_id[int(tid)] for tid in ordered_task_ids]
        _reindex_items(milestone["tasks"], "id")
        _refresh_completion_flags(plan)

        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

    def apply_task_completion_activity(self, plan_id: str, owner_user_id: int | None = None) -> dict | None:
        """
        Call this when at least one task was marked completed today.
        """
        plan = self.load_plan(plan_id, owner_user_id=owner_user_id)
        if plan is None:
            return None

        # Use UTC day boundaries consistently to avoid server timezone drift.
        _update_streak_for_activity(plan, _utc_today())

        # Persist streak update.
        self.save_plan_direct(plan_id, plan, owner_user_id=owner_user_id, bypass_owner_check=True)
        return plan

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
