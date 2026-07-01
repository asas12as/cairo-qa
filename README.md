# Cairo Places QA

Local Q&A system over Egyptian places data using a hybrid RAG + local LLM approach.

## Setup

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy dev config as default
copy config.dev.yaml config.yaml

# 3. Download a local LLM model
.\scripts\download_models.ps1 -Mode dev   # Phi-3-mini (~2.2GB, laptop)
.\scripts\download_models.ps1 -Mode prod  # Llama 3.1 8B (~4.9GB, PC with GPU)

# 4. Place your CSV in data/raw/

# 5. Ingest the data
python main.py --ingest data\raw\your_file.csv

# 6. Start the server
python main.py
# Server runs at http://localhost:8000
```

## API

| Endpoint | Description |
|---|---|
| `POST /ask` | Ask a question: `{"question": "..."}` |
| `POST /feedback` | Rate answer: `{"conversation_id": "...", "rating": 5}` |
| `GET /stats` | System statistics |

## Switching Configs

Laptop (CPU): `copy config.dev.yaml config.yaml`
PC with GPU:  `copy config.prod.yaml config.yaml`

## Continuous Learning

1. Conversations are auto-logged to `data/conversations/`
2. Users can submit feedback via `/feedback`
3. Run `python -m learning.data_prep` to prepare training data
4. Run `python -m learning.finetune --base-model models_cache/...` to fine-tune
