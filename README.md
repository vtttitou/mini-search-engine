# Mini Search Engine

An English document search application that implements **TF-IDF with cosine similarity** and **BM25**, supported by an inverted index. The project combines a web interface for searching uploaded documents with experiments on the NFCorpus dataset.

Developed for **Project I** by **Thip Peahouvitou**.

## Objectives

- Implement and understand lexical document retrieval.
- Compare TF-IDF and BM25 using relevance judgments.
- Investigate how term weighting, normalization, stopwords, and searchable fields affect retrieval.
- Analyze search efficiency and unsuccessful queries.

## Features

- Create and manage document collections.
- Upload TXT and text-based PDF files.
- Search using TF-IDF or BM25.
- Display ranked results, matching snippets, and extracted document text.
- Run reproducible retrieval experiments and export evaluation results.

## Technologies

| Component | Technology |
|---|---|
| Search algorithms and evaluation | Python, NumPy, SciPy |
| Backend API | FastAPI, Uvicorn |
| Document storage | SQLite and local files |
| PDF text extraction | pypdf |
| Frontend | HTML, CSS, JavaScript |
| Testing | pytest |

SQLite stores document metadata and extracted text. Search indexes are maintained in memory and rebuilt when required.

## Project Structure

| Path | Purpose |
|---|---|
| `engine/` | Text preprocessing, inverted index, ranking algorithms, and evaluation metrics |
| `backend/` | API endpoints, file processing, and database operations |
| `frontend/` | Browser interface for collections, uploads, and search |
| `data/` | Dataset source information and sample data |
| `tests/` | Algorithm and API tests |
| `run.py` | Starts the web application |
| `experiment.py` | Downloads data, runs experiments, and searches the benchmark |
| `results/` | Generated experiment outputs; excluded from Git by default |

Downloaded NFCorpus data and runtime uploads are also excluded from Git.

## Run the Application

Use Python 3.12. From the project directory on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Open **http://127.0.0.1:8000**.

Create a collection, upload documents, select a ranking method, and enter a query. Interactive API documentation is available at **http://127.0.0.1:8000/docs**.

## Dataset and Evaluation

The project uses the **BEIR version of NFCorpus**, an English medical and nutrition retrieval dataset containing **3,633 documents**, represented by titles and abstracts.

It includes search queries and relevance judgments (`qrels`), allowing ranked results to be evaluated against known relevant documents. The development split contains **324 queries**.

Experiments compare TF-IDF and BM25 and examine individual TF-IDF variations:

- Logarithmic term frequency
- Removal of vector normalization
- Retention of stopwords
- Title-only or abstract-only searching

Evaluation includes **nDCG@10**, **Recall@100**, **MAP@100**, **MRR@10**, and **Precision@10**, alongside index construction time and query latency.

Settings are selected on the development set. The test set is reserved for final evaluation.

### Run Experiments

Download the dataset for a fresh checkout:

```powershell
.\.venv\Scripts\python.exe experiment.py download
```

Run the development comparison and TF-IDF variations:

```powershell
.\.venv\Scripts\python.exe experiment.py evaluate --split dev --ablation
```

Try an individual query:

```powershell
.\.venv\Scripts\python.exe experiment.py search --method bm25 --query "breast cancer"
```

Outputs are saved under `results/`, including `summary.csv`, experiment settings, document rankings, and per-query metrics. Query timings measure local retrieval rather than the complete website response.



## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest -q
```


