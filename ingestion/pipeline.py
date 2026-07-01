import re

import pandas as pd

from retrieval.structured_db import StructuredDB
from retrieval.vector_store import VectorStore


def parse_budget_range(budget_str: str) -> tuple[int | None, int | None]:
    if not budget_str or str(budget_str).strip().upper() in ("N/A", "", "NONE"):
        return None, None
    text = str(budget_str).replace(",", "").replace("EGP", "").strip()
    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    if nums:
        val = int(nums[0])
        return val, val
    return None, None


def ingest_csv(csv_path: str, structured_db: StructuredDB, vector_store: VectorStore) -> int:
    df = pd.read_csv(csv_path)

    records = []
    for _, row in df.iterrows():
        min_b, max_b = parse_budget_range(row.get("Budget Range (EGP)", ""))
        records.append((
            str(row.get("Category", "")).strip(),
            str(row.get("Name", "")).strip(),
            str(row.get("Neighborhood", "")).strip(),
            str(row.get("Address", "")).strip(),
            _safe_float(row.get("Latitude")),
            _safe_float(row.get("Longitude")),
            _safe_float(row.get("Rating")),
            _safe_int(row.get("Rating Count")),
            str(row.get("Genre / Type", "")).strip(),
            str(row.get("Budget Level", "")).strip(),
            min_b,
            max_b,
            str(row.get("Work Hours", "")).strip(),
            str(row.get("Phone", "")).strip(),
            str(row.get("Notes", "")).strip(),
        ))

    structured_db.insert_many(records)

    all_places = structured_db.get_all()
    vector_store.add_places(all_places)

    return len(records)


def _safe_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0
