# Biolens
### AI-Powered Gene Expression Analysis Platform

[![Python](https://img.shields.io/badge/Python-3.10-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

An end-to-end bioinformatics platform for querying, analyzing, and interpreting TCGA breast cancer gene expression data. Combines a PostgreSQL relational database, FastAPI REST API, Claude-powered LLM agent, and an interactive Streamlist UI.

** [Live API Docs](http://YOUR_EC2_IP:8000/docs)** (if deployed)

---

## Features

| Feature | Description |
|---|---|
|  PostgreSQL database | 15K genes × 1,218 TCGA-BRCA samples |
|  FastAPI REST API | Expression queries, DE analysis, pathway enrichment |
|  Claude LLM | Natural language biological interpretation |
|  LangChain agent | Autonomous multi-step analysis workflows |
|  ChromaDB search | Semantic gene search by biological function |
|  ML classifier | GradientBoosting PAM50 subtype prediction (XX% accuracy) |
|  AWS deployment | EC2 + S3 + Docker |
|  Streamlit UI | Interactive visual interface |

## Tech Stack
Python · FastAPI · PostgreSQL · LangChain · Anthropic Claude API ·
ChromaDB · scikit-learn · AWS (EC2/S3) · Docker · Streamlit · Plotly

## Quick Start

```bash
git clone https://github.com/SanchithaK/biolens.git
cd biolens
cp .env.example .env        # Add your API keys
sudo service postgresql start
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
streamlit run app.py
```

## Screenshots

[Add screenshots here]


## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/expression/{gene}` | GET | Expression values by sample/stage |
| `/expression/samples` | GET | List samples with filters |
| `/expression/search/semantic` | GET | Vector similarity gene search |
| `/analysis/differential` | POST | DE analysis between groups |
| `/analysis/classify/{sample_id}` | GET | ML cancer subtype prediction |
| `/chat/ask` | POST | Claude AI interpretation |

## Data
Uses publicly available TCGA-BRCA RNA-seq data (1,218 samples).
Download from [UCSC Xena](https://xenabrowser.net/datapages/).
