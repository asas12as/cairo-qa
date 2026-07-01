import json
from datetime import datetime
from pathlib import Path


class ConversationLogger:
    def __init__(self, log_dir: str = "data/conversations"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _today_file(self) -> Path:
        today = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"conversations_{today}.jsonl"

    def _all_files(self) -> list[Path]:
        return sorted(self.log_dir.glob("conversations_*.jsonl"))

    def log(self, conv_id: str, question: str, route_info: dict, context: list[dict], answer: str):
        entry = {
            "conversation_id": conv_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "filters_used": route_info.get("filters", {}),
            "semantic_query": route_info.get("semantic_query", ""),
            "retrieved_count": len(context),
            "retrieved_names": [r.get("name", "") for r in context[:5]],
            "answer": answer,
            "feedback": None,
            "corrected_answer": None,
        }
        with open(self._today_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_feedback(self, conv_id: str, rating: int, corrected_answer: str | None = None):
        for log_file in self._all_files():
            temp_file = log_file.with_suffix(".tmp")
            found = False
            with open(log_file, "r", encoding="utf-8") as f_in, \
                 open(temp_file, "w", encoding="utf-8") as f_out:
                for line in f_in:
                    entry = json.loads(line)
                    if entry["conversation_id"] == conv_id and not found:
                        entry["feedback"] = rating
                        entry["corrected_answer"] = corrected_answer
                        found = True
                    f_out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            if found:
                temp_file.replace(log_file)
                return

    def count(self) -> int:
        total = 0
        for f in self._all_files():
            with open(f, encoding="utf-8") as fh:
                total += sum(1 for _ in fh)
        return total

    def get_all(self) -> list[dict]:
        entries = []
        for f in self._all_files():
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    entries.append(json.loads(line))
        return entries
