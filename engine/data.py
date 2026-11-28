import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path):
    rows = {}
    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            key = str(row["_id"])
            if key in rows:
                raise ValueError(f"Duplicate ID: {key}")
            rows[key] = row
    return rows


def load_data(folder, split="dev"):
    folder = Path(folder)
    corpus = read_jsonl(folder / "corpus.jsonl")
    queries = read_jsonl(folder / "queries.jsonl")
    qrels = {}
    with (folder / "qrels" / f"{split}.tsv").open(encoding="utf-8") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            query, doc, grade = str(row["query-id"]), str(row["corpus-id"]), int(row["score"])
            if query not in queries or doc not in corpus or grade < 0:
                raise ValueError(f"Invalid relevance judgment: {row}")
            if doc in qrels.get(query, {}):
                raise ValueError(f"Duplicate judgment: {query}, {doc}")
            qrels.setdefault(query, {})[doc] = grade
    selected = {key: row["text"] for key, row in queries.items() if any(g > 0 for g in qrels.get(key, {}).values())}
    if not corpus or not selected:
        raise ValueError("Need documents and queries with positive relevance judgments")
    return corpus, selected, qrels


def fingerprints(folder, split):
    names = ["corpus.jsonl", "queries.jsonl", f"qrels/{split}.tsv"]
    result = {}
    for name in names:
        digest = hashlib.sha256()
        with (Path(folder) / name).open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        result[name] = digest.hexdigest()
    return result
