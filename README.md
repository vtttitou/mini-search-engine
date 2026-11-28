# Mini Search Engine: TF-IDF and BM25

A small English document-search application and a reproducible research project. It searches TXT and text-based PDF files, and compares TF-IDF cosine similarity with BM25 on NFCorpus. The goal is to understand the algorithms and explain their results.

## Start on Windows

Extract this ZIP into a new folder. Keep your original project separately. Open this folder in VS Code and open a terminal in it.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:8000. Create a collection, upload files, type a query, choose TF-IDF or BM25, and press Search. The first search after an upload builds the indexes. Stop the server with Ctrl+C. No environment activation is required for these commands. Use Python 3.12 for the pinned dependency versions in this package; the code and tests were checked with Python 3.12.

On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python` instead of the Windows executable path.

Do not double-click index.html: the interface needs the running Python API.

## The structure

| Path | Purpose |
|---|---|
| `run.py` | Starts the local web server. |
| `experiment.py` | One command-line entry point for dataset statistics, experiments, data download, and benchmark searches. |
| `requirements.txt` | Runtime libraries to install with pip. |
| `requirements-test.txt` | Extra libraries for testing and reference comparisons. |
| `engine/text.py` | English tokenization and the stopword list. |
| `engine/index.py` | Inverted index, document lengths, query counts, and top-k selection. |
| `engine/tfidf.py` | TF-IDF weighting and cosine normalization. |
| `engine/bm25.py` | BM25 weights and search. |
| `engine/data.py` | Read and validate corpus, queries, and relevance labels; hash input files. |
| `engine/metrics.py` | Calculate retrieval evaluation metrics. |
| `engine/__init__.py` | Makes engine an importable Python package. |
| `backend/app.py` | API routes, collection operations, index cache, and search results. |
| `backend/database.py` | SQLite connections and the two database tables. |
| `backend/files.py` | Validate files and extract TXT/PDF text. |
| `backend/__init__.py` | Makes backend an importable Python package. |
| `frontend/index.html` | Three sections: collection, documents, and search. |
| `frontend/css/style.css` | Simple visual layout. |
| `frontend/js/app.js` | Initializes the interface. |
| `frontend/js/api.js` | Sends HTTP requests to the API. |
| `frontend/js/state.js` | Remembers the selected collection and shows errors. |
| `frontend/js/collections.js` | Create, switch, and delete collections. |
| `frontend/js/upload.js` | Upload, list, and delete documents. |
| `frontend/js/search.js` | Search, display results, highlight text, and expand full text. |
| `data/nfcorpus/` | Included benchmark documents, queries, and qrels. |
| `data/sample/` | Small 14-document fixture for quick checks; not a benchmark result. |
| `results/` | One folder per experiment: settings, scores, rankings, examples, and timings. |
| `docs/algorithms.md` | Formulas, a worked example, and reading order. |
| `docs/results.md` | Measured results, explanations, limits, and the next research plan. |
| `docs/performance.md` | Timing checks, complexity, and scaling limits. |
| `docs/presentation.md` | Likely professor questions and answers. |
| `docs/previous_results.csv` | Historical table from the original project, kept separate from fresh results. |
| `docs/speed_measurements.json` | Raw synthetic timing observations, including slower cases. |
| `data/SOURCE.md` | Dataset provenance, format, and attribution. |
| `tests/test_search.py` | Algorithm and metric correctness checks. |
| `tests/test_app.py` | Upload/search/delete and API checks. |
| `.gitignore` | Excludes environments, runtime files, downloaded data, and generated runs from Git. |
| `LICENSE` | Code license inherited from the source project. |

`runtime/` is created when the server starts. It contains `app.db` and uploaded files. It is not included in this ZIP. All source files are normal Python modules: no YAML configuration, Makefile, package installation, or .env file is needed.

## Technologies

- Python implements document processing, ranking, evaluation, and the API.
- NumPy performs array calculations and efficient top-k selection.
- SciPy stores term-document counts as a compressed sparse row (CSR) matrix. Rows are terms; columns are documents. A row is the postings list for a term. Missing term-document pairs occupy no explicit value slot.
- FastAPI exposes HTTP endpoints and validates request parameters.
- Uvicorn runs FastAPI locally.
- SQLite, accessed with Python's sqlite3 module, persists application records.
- pypdf extracts existing PDF text layers. It does not perform OCR.
- HTML/CSS/JavaScript implement the browser interface without a framework.
- pytest and scikit-learn are test-only dependencies. Scikit-learn checks TF-IDF against a reference; it does not implement the application's ranking.

## Database and storage

`collections`: `id`, unique `name`, `created_at`.

`documents`: `id`, `collection_id`, `filename`, `stored_path`, `size_bytes`, `num_chars`, extracted `text`, `created_at`.

One collection has many documents. The foreign key uses cascading deletion. An SQL index on `collection_id` speeds collection lookups. This SQL index is different from the search inverted index.

Original uploads are stored under generated IDs in `runtime/uploads/<collection_id>/`. SQLite stores metadata and extracted text. Search indexes live in memory and are rebuilt from SQLite after a server restart. No pickle files are loaded.

The application caches at most four collections, keeping both algorithms for each collection. Upload/delete operations invalidate that collection's cache. The next search builds it again. This keeps IDF and BM25 statistics consistent with the documents. Search requests do not extract PDF text again.

This is a local single-user application. Run one server process. A lock serializes database/index operations; there is no authentication, distributed cache, background queue, or multi-user isolation. A four-collection cache is not a strict byte limit: one very large collection can still use substantial RAM.

## Upload and search workflow

1. Create a collection.
2. Upload UTF-8 TXT or unencrypted, text-based PDF files.
3. Validate each file, extract its text, save the original, and insert its database record.
4. Clear any old collection index.
5. Search builds an index if necessary, calculates scores, and returns the highest positive scores.
6. The frontend displays filename, score, snippet, and a Full text button.

Limits are 10 MB per file and 20 files per upload, defined in `backend/files.py`. Unsupported files are listed in the upload response. Scanned PDFs, DOCX, images, and non-UTF-8 text are not supported. File-size limits do not guarantee a small extracted text size for every PDF.

Both algorithms use the same tokenizer and stopwords. The default field is title plus text. For uploads the filename acts as the title. The tokenizer is English-oriented (`[a-z0-9]+`), not suitable for Vietnamese/Khmer search. There is no fuzzy search, Boolean AND/OR mode, phrase constraint, or semantic search. Documents matching any query term can receive positive lexical scores.

## API

Interactive documentation is at http://127.0.0.1:8000/docs.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check server status. |
| GET | `/api/methods` | List TF-IDF and BM25. |
| GET / POST | `/api/collections` | List or create collections. |
| DELETE | `/api/collections/{id}` | Delete a collection and its documents. |
| GET / POST | `/api/collections/{id}/documents` | List or upload documents. |
| GET / DELETE | `/api/collections/{id}/documents/{doc_id}` | Read extracted text or delete a document. |
| GET | `/api/collections/{id}/search?q=apple&method=bm25&k=10` | Search a collection. |

Create a collection with JSON `{"name":"My notes"}`. Upload uses multipart form data with one or more `files` fields. Search accepts `q` (1–500 characters, not whitespace only), `method` (`tfidf` or `bm25`), and `k` (1–100).

`search_ms` measures ranking only. It excludes database access, snippets, network traffic, browser rendering, and any initial index build. `index_build_ms` is reported separately and includes preparing both algorithms in the web application. Scores from different methods or different queries are not interchangeable confidence percentages.

## Research commands

The real NFCorpus data and a development ablation run are included. The test split has not been used for model selection or final scoring in this version.

```powershell
.\.venv\Scripts\python.exe experiment.py describe
.\.venv\Scripts\python.exe experiment.py evaluate
.\.venv\Scripts\python.exe experiment.py evaluate --ablation
.\.venv\Scripts\python.exe experiment.py search --method bm25 --query "breast cancer"
```

Try other settings on dev:

```powershell
.\.venv\Scripts\python.exe experiment.py evaluate --k1 1.5 --b 0.9
.\.venv\Scripts\python.exe experiment.py evaluate --log-tf
.\.venv\Scripts\python.exe experiment.py evaluate --keep-stopwords
```

`--ablation` runs seven fixed variants; it defines the TF-IDF switches itself. Use standalone evaluate commands for other combinations. Defaults are in function arguments and command-line defaults, not a hidden configuration directory.

After choosing settings on dev, record them and run the final comparison:

```powershell
.\.venv\Scripts\python.exe experiment.py evaluate --split test
```

Add your selected flags to that command. Do not tune based on test scores. The corpus is shared across splits; the queries and relevance labels define train/dev/test. TF-IDF and BM25 do not learn supervised weights from qrels.

For a quick software check:

```powershell
.\.venv\Scripts\python.exe experiment.py evaluate --data data/sample
```

If restoring data to a fresh checkout, `python experiment.py download` downloads the official BEIR ZIP. It refuses to overwrite an existing data/nfcorpus folder. The official server returned HTTP 503 during preparation, so this package includes a Hugging Face copy instead; see `data/SOURCE.md` for exact sources. You can also place BEIR-format corpus.jsonl, queries.jsonl, and qrels files into data/nfcorpus manually.

## Experiment output

Each timestamped folder contains:

- `settings.json`: arguments, split, versions, and SHA-256 hashes of corpus, queries, and selected qrels.
- `summary.csv` / `summary.json`: average metrics and timing for each method.
- `<method>_rankings.jsonl`: top 100 scored documents per query.
- `<method>_per_query.csv`: metrics for every evaluated query.
- `<method>_examples.json`: five best and five worst queries with document titles and known relevance grades.
- `query_comparison.csv`: per-query nDCG differences between BM25 and the TF-IDF baseline.

The runner performs five warm-up queries. Each query is timed three times by default and its median latency is used in the aggregate timing. Build time is a single measurement. Timings depend on hardware and are not end-to-end API response times.

The ablation compares normalized raw-TF TF-IDF, BM25, TF-IDF without normalization, logarithmic TF, keeping stopwords, title-only, and text-only retrieval. Each TF-IDF variant changes one factor from the baseline. Both main methods use identical preprocessing.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest -q
```

15 tests passed in the preparation environment. Tests check cosine scores against scikit-learn, hand-calculated BM25 and metrics, tie handling, empty/OOV queries, normalization, API validation, and upload/search/delete cache behavior. Passing tests checks implementation behavior, not search quality on an unseen dataset.

## Reading order

Read `engine/text.py`, then `engine/index.py`, `engine/tfidf.py`, `engine/bm25.py`, `engine/metrics.py`, and `experiment.py`. After understanding the research flow, read backend/database.py, backend/files.py, and backend/app.py. The frontend is a client of the API.

## Scope and next steps

Focus on explaining TF-IDF and BM25, evaluating settings on dev, and inspecting failures. The research notes discuss semantic retrieval as future work, not an implemented feature. Large deployments would require additional indexing, memory, concurrency, and update strategies. This program does not guarantee constant search time for arbitrarily large datasets.

Source code derives from the supplied mini-search-engine project. Keep its license notice. Dataset attribution and license are separate; see data/SOURCE.md. Report experiments you actually ran and explain the implementation and any assistance according to your course requirements.
