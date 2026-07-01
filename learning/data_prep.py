import json
from pathlib import Path


def prepare_finetune_data(
    log_dir: str = "data/conversations",
    output_path: str = "data/finetune/training.jsonl",
    min_rating: int = 3,
) -> int:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for f in sorted(Path(log_dir).glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                entry = json.loads(line)
                fb = entry.get("feedback")
                if fb is not None and int(fb) >= min_rating:
                    entries.append(entry)

    with open(output_path, "w", encoding="utf-8") as f_out:
        for entry in entries:
            answer = entry.get("corrected_answer") or entry["answer"]
            train_entry = {
                "instruction": entry["question"],
                "output": answer,
                "system": "You are a Cairo/Egypt places expert. Answer using the database.",
            }
            f_out.write(json.dumps(train_entry, ensure_ascii=False) + "\n")

    return len(entries)
