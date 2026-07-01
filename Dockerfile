FROM python:3.11-slim

WORKDIR /app

# Create data directory (required for DuckDB path even without volume)
RUN mkdir -p /data

# Install build deps (needed for sentence-transformers / torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Pre-download the embedder model (avoids slow download on first start)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Environment defaults
ENV CONFIG_PATH=/app/config.docker.yaml \
    DATA_DIR=/data \
    DB_PATH=/data/places.duckdb \
    VECTOR_STORE_PATH=/data/chroma_db \
    CSV_DIR=/app/data/csv

EXPOSE 8000

CMD ["bash", "entrypoint.sh"]
