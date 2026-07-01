import duckdb


class StructuredDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = duckdb.connect(self.db_path)

    def create_table(self):
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS place_id_seq START 1
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER DEFAULT nextval('place_id_seq'),
                category VARCHAR,
                name VARCHAR,
                neighborhood VARCHAR,
                address VARCHAR,
                latitude DOUBLE,
                longitude DOUBLE,
                rating DOUBLE,
                rating_count INTEGER,
                genre_type VARCHAR,
                budget_level VARCHAR,
                budget_range_min INTEGER,
                budget_range_max INTEGER,
                work_hours VARCHAR,
                phone VARCHAR,
                notes VARCHAR
            )
        """)

    def insert_many(self, records: list[tuple]):
        self.conn.executemany("""
            INSERT INTO places (
                category, name, neighborhood, address, latitude, longitude,
                rating, rating_count, genre_type, budget_level,
                budget_range_min, budget_range_max, work_hours, phone, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

    def query(self, filters: dict | None = None, limit: int = 20) -> list[dict]:
        query = "SELECT * FROM places WHERE 1=1"
        params = []

        if filters:
            if "category" in filters and filters["category"]:
                query += " AND LOWER(category) = LOWER(?)"
                params.append(filters["category"])
            if "neighborhood" in filters and filters["neighborhood"]:
                query += " AND LOWER(neighborhood) LIKE LOWER(?)"
                params.append(f"%{filters['neighborhood']}%")
            if "max_budget" in filters and filters["max_budget"] is not None:
                query += " AND budget_range_min <= ?"
                params.append(int(filters["max_budget"]))
            if "min_budget" in filters and filters["min_budget"] is not None:
                query += " AND budget_range_max >= ?"
                params.append(int(filters["min_budget"]))
            if "min_rating" in filters and filters["min_rating"] is not None:
                query += " AND rating >= ?"
                params.append(float(filters["min_rating"]))
            if "genre" in filters and filters["genre"]:
                query += " AND LOWER(genre_type) LIKE LOWER(?)"
                params.append(f"%{filters['genre']}%")
            if "ids" in filters and filters["ids"]:
                placeholders = ",".join("?" for _ in filters["ids"])
                query += f" AND id IN ({placeholders})"
                params.extend(filters["ids"])

        query += " ORDER BY rating DESC NULLS LAST LIMIT ?"
        params.append(limit)

        result = self.conn.execute(query, params)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_all(self) -> list[dict]:
        result = self.conn.execute("SELECT * FROM places")
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]

    def insert_place(self, data: dict) -> int:
        self.conn.execute("""
            INSERT INTO places (
                category, name, neighborhood, address, latitude, longitude,
                rating, rating_count, genre_type, budget_level,
                budget_range_min, budget_range_max, work_hours, phone, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("category", ""), data.get("name", ""),
            data.get("neighborhood", ""), data.get("address", ""),
            data.get("latitude", 0.0), data.get("longitude", 0.0),
            data.get("rating", 0.0), data.get("rating_count", 0),
            data.get("genre_type", ""), data.get("budget_level", ""),
            data.get("budget_range_min", 0), data.get("budget_range_max", 0),
            data.get("work_hours", ""), data.get("phone", ""),
            data.get("notes", ""),
        ))
        result = self.conn.execute("SELECT MAX(id) FROM places").fetchone()[0]
        return result if result else 1

    def update_place(self, place_id: int, data: dict):
        allowed = {"category", "name", "neighborhood", "address", "latitude", "longitude",
                   "rating", "rating_count", "genre_type", "budget_level",
                   "budget_range_min", "budget_range_max", "work_hours", "phone", "notes"}
        sets = []
        params = []
        for k, v in data.items():
            if k in allowed and v is not None:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return
        params.append(place_id)
        self.conn.execute(f"UPDATE places SET {', '.join(sets)} WHERE id = ?", params)

    def delete_place(self, place_id: int):
        self.conn.execute("DELETE FROM places WHERE id = ?", (place_id,))

    def close(self):
        if self.conn:
            self.conn.close()
