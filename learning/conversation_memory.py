import json
import os
from datetime import datetime


MAX_HISTORY = 10


class ConversationMemory:
    """Per-user rolling conversation history stored as JSON files."""

    def __init__(self, data_dir: str):
        self.data_dir = os.path.join(data_dir, "conversation_history")
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return os.path.join(self.data_dir, f"{safe}.json")

    def get_history(self, user_id: str) -> list[dict]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def add_exchange(self, user_id: str, question: str, answer: str):
        path = self._path(user_id)
        history = self.get_history(user_id)
        history.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
        })
        # Keep only last N
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_accumulated_params(self, user_id: str, current_question: str) -> tuple[int | None, int | None]:
        """Scan history for budget and days if current question is missing them."""
        import re
        from agent.query_router import (BUDGET_PATTERN, DAYS_PATTERN, FOR_X_DAYS,
                                        BARE_BUDGET, ARABIC_BUDGET, ARABIC_BARE_BUDGET,
                                        ARABIC_DAYS, ARABIC_DIGITS)

        def _find_budget(text: str, norm: str) -> int | None:
            m = BUDGET_PATTERN.search(norm)
            if not m:
                m = ARABIC_BUDGET.search(norm)
            if not m:
                m = ARABIC_BARE_BUDGET.search(norm)
            if not m:
                m = BARE_BUDGET.search(text)
            if not m:
                m = FOR_X_DAYS.search(norm)
            if not m:
                m = re.search(r"(?:^|\s)(\d{3,6})(?:\s|$)", norm)
            return int(m.group(1)) if m else None

        def _find_days(text: str, norm: str) -> int | None:
            m = DAYS_PATTERN.search(norm)
            if m:
                return int(m.group(1))
            m = FOR_X_DAYS.search(norm)
            if m:
                return int(m.group(2))
            day_match = ARABIC_DAYS.search(norm)
            if day_match:
                before = norm[:day_match.start()]
                digits = re.findall(r"(\d+)", before)
                if digits:
                    return int(digits[-1])
            return None

        q_norm = current_question.lower().translate(ARABIC_DIGITS)
        cur_budget = _find_budget(current_question.lower(), q_norm)
        cur_days = _find_days(current_question.lower(), q_norm)

        if cur_budget is not None and cur_days is not None:
            return cur_budget, cur_days

        for entry in reversed(self.get_history(user_id)):
            prev_q = entry.get("question", "")
            prev_norm = prev_q.lower().translate(ARABIC_DIGITS)

            if cur_budget is None:
                cur_budget = _find_budget(prev_q.lower(), prev_norm)
            if cur_days is None:
                cur_days = _find_days(prev_q.lower(), prev_norm)
            if cur_budget is not None and cur_days is not None:
                break

        return cur_budget, cur_days
