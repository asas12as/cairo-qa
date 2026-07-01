import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import pandas as pd
from retrieval.structured_db import StructuredDB
from retrieval.vector_store import VectorStore

USD_TO_EGP = 50


def _parse_range_usd(value: str) -> tuple[int | None, int | None]:
    """Parse '14-20' or '32' or 'Varies' or 'Free' -> (min_egp, max_egp)."""
    if pd.isna(value) or str(value).strip().lower() in ("", "varies", "free", "n/a", "none"):
        return None, None
    nums = re.findall(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not nums:
        return None, None
    vals = [int(round(float(n) * USD_TO_EGP)) for n in nums]
    if len(vals) >= 2:
        return vals[0], vals[1]
    return vals[0], vals[0]


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    return "N/A" if s.lower() in ("", "nan", "none", "n/a") else s


def load_attractions(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        min_b, max_b = _parse_range_usd(row.get("entry_fee_usd", ""))
        notes = _safe_str(row.get("description", ""))
        est_time = row.get("estimated_time", "")
        if not pd.isna(est_time):
            notes = f"{notes} | Time: {est_time}" if notes else f"Time: {est_time}"
        records.append((
            "attraction",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            "",  # address
            None,  # lat
            None,  # lng
            _safe_float(row.get("rating")),
            None,  # rating_count
            _safe_str(row.get("category", "")),
            price_level(min_b, max_b),
            min_b,
            max_b,
            "",  # work_hours
            "",  # phone
            notes,
        ))
    return records


def load_hotels(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        min_b, max_b = _parse_range_usd(row.get("price_range_per_night_usd", ""))
        star = _safe_float(row.get("star_rating"))
        rating = star if star else None
        records.append((
            "hotel",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            _safe_str(row.get("location", "")),
            None, None,
            rating,
            None,
            "",  # genre_type for hotels
            _safe_str(row.get("budget_category", "")),
            min_b,
            max_b,
            "",  # work_hours
            "",  # phone
            _safe_str(row.get("description", "")),
        ))
    return records


def load_museums(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        min_b, max_b = _parse_range_usd(row.get("entry_fee_usd", ""))
        notes = _safe_str(row.get("description", ""))
        est_time = row.get("estimated_time", "")
        if not pd.isna(est_time):
            notes = f"{notes} | Time: {est_time}" if notes else f"Time: {est_time}"
        records.append((
            "attraction",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            "", None, None,
            _safe_float(row.get("rating")),
            None,
            "Museum",
            price_level(min_b, max_b),
            min_b,
            max_b,
            "", "",
            notes,
        ))
    return records


def load_nightlife(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        records.append((
            "restaurant" if "restaurant" in str(row.get("type", "")).lower() else "attraction",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            "", None, None,
            None,  # no rating
            None,
            _safe_str(row.get("type", "")),
            "",  # budget_level
            None, None,
            "", "",
            _safe_str(row.get("description", "")),
        ))
    return records


def load_restaurants(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        min_b, max_b = _parse_range_usd(row.get("price_range_per_person_usd", ""))
        records.append((
            "restaurant",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            "", None, None,
            _safe_float(row.get("rating")),
            None,
            _safe_str(row.get("cuisine", "")),
            price_level(min_b, max_b),
            min_b,
            max_b,
            "", "",
            _safe_str(row.get("description", "")),
        ))
    return records


def load_shopping(path: Path) -> list[tuple]:
    df = pd.read_csv(path, on_bad_lines="skip")
    records = []
    for _, row in df.iterrows():
        records.append((
            "attraction",
            _safe_str(row["name"]),
            _safe_str(row.get("area", "")),
            "", None, None,
            None, None,
            "Shopping",
            "", None, None,
            "", "",
            _safe_str(row.get("description", "")),
        ))
    return records


def price_level(min_b: int | None, max_b: int | None) -> str:
    if min_b is None:
        return ""
    avg = (min_b + (max_b or min_b)) / 2
    if avg < 250:
        return "Budget"
    if avg < 1000:
        return "Mid-range"
    if avg < 3000:
        return "Upscale"
    return "Luxury"


def deduplicate(records: list[tuple]) -> list[tuple]:
    seen = set()
    result = []
    for r in records:
        key = r[1].lower().strip()  # name
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def replace_all(data_dir: str, structured_db: StructuredDB, vector_store: VectorStore):
    data_path = Path(data_dir)

    print("Dropping old data...")
    structured_db.conn.execute("DROP TABLE IF EXISTS places")
    structured_db.create_table()

    all_records = []
    loaders = [
        (load_attractions, "attractions.csv"),
        (load_hotels, "hotels.csv"),
        (load_museums, "museums.csv"),
        (load_nightlife, "nightlife.csv"),
        (load_restaurants, "restaurants.csv"),
        (load_shopping, "shopping.csv"),
    ]
    for loader_fn, filename in loaders:
        filepath = data_path / filename
        if filepath.exists():
            recs = loader_fn(filepath)
            print(f"  {filename}: {len(recs)} rows")
            all_records.extend(recs)
        else:
            print(f"  {filename}: NOT FOUND")

    all_records = deduplicate(all_records)
    print(f"Total after dedup: {len(all_records)}")

    structured_db.insert_many(all_records)
    print("Inserted into DuckDB.")

    all_places = structured_db.get_all()
    vector_store.delete_collection()
    vector_store.get_or_create_collection()
    vector_store.add_places(all_places)
    print(f"Rebuilt ChromaDB with {len(all_places)} places.")

    return len(all_places)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import Config
    from models.embedder import Embedder

    config = Config(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")

    print("Connecting to DB...")
    db = StructuredDB(config.db.path)
    db.connect()
    db.create_table()

    print("Loading embedder...")
    embedder = Embedder(config.embedder.model)

    print("Connecting to vector store...")
    vs = VectorStore(config.vector_store.path, config.vector_store.collection, embedder)
    vs.get_or_create_collection()

    csv_dir = sys.argv[2] if len(sys.argv) > 2 else "J:/New folder/testData"
    count = replace_all(csv_dir, db, vs)
    print(f"\nDone. {count} places loaded.")
    db.close()
