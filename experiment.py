import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import platform
import time
import urllib.request
import zipfile

import numpy as np
import scipy
from engine.data import ROOT, fingerprints, load_data, read_jsonl
from engine.index import InvertedIndex
from engine.tfidf import TFIDF
from engine.bm25 import BM25
from engine.metrics import evaluate_ranking
from engine.text import tokenize

METRICS = ["ndcg@10", "recall@10", "recall@100", "map@100", "mrr@10", "precision@10"]
URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/nfcorpus.zip"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def download():
    folder = ROOT / "data"
    target = folder / "nfcorpus"
    if target.exists():
        raise ValueError("data/nfcorpus already exists; move it aside before downloading again")
    archive = folder / "nfcorpus.zip"
    urllib.request.urlretrieve(URL, archive)
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            if not (folder / entry.filename).resolve().is_relative_to(folder.resolve()):
                raise ValueError("Unsafe path in dataset archive")
        source.extractall(folder)
    archive.unlink()
    print(f"Dataset saved to {target}")


def describe(folder):
    documents = read_jsonl(folder / "corpus.jsonl")
    lengths = [len(tokenize(doc.get("title", "") + " " + doc.get("text", ""), False)) for doc in documents.values()]
    statistics = {"documents": len(documents), "mean_tokens_before_stopwords": float(np.mean(lengths)), "median_tokens_before_stopwords": float(np.median(lengths)), "empty_text": sum(not doc.get("text", "").strip() for doc in documents.values()), "splits": {}}
    for split in ("train", "dev", "test"):
        _, queries, qrels = load_data(folder, split)
        statistics["splits"][split] = {"evaluated_queries": len(queries), "judgments": sum(len(qrels[q]) for q in queries), "grades": dict(Counter(g for q in queries for g in qrels[q].values()))}
    print(json.dumps(statistics, indent=2))
    return statistics


def evaluate(args):
    corpus, queries, qrels = load_data(args.data, args.split)
    if args.ablation and args.split != "dev":
        raise ValueError("Run ablations on dev, not test")
    settings = vars(args).copy()
    settings["data"] = str(args.data)
    settings["created_at"] = datetime.now(timezone.utc).isoformat()
    settings["hashes"] = fingerprints(args.data, args.split)
    settings["versions"] = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}
    settings["documents"] = len(corpus)
    settings["queries"] = len(queries)
    folder = ROOT / "results" / (args.data.name + "_" + args.split + "_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(parents=True)
    write_json(folder / "settings.json", settings)
    variants = [("tfidf", args.fields, not args.keep_stopwords, args.normalize, args.log_tf), ("bm25", args.fields, not args.keep_stopwords, True, False)]
    if args.ablation:
        variants = [("tfidf", "title_text", True, True, False), ("bm25", "title_text", True, True, False), ("tfidf_no_norm", "title_text", True, False, False), ("tfidf_log", "title_text", True, True, True), ("tfidf_keep_stopwords", "title_text", False, True, False), ("tfidf_title", "title", True, True, False), ("tfidf_text", "text", True, True, False)]
    summary, comparisons = [], {}
    for name, fields, stopwords, normalize, log_tf in variants:
        start = time.perf_counter()
        index = InvertedIndex(corpus, stopwords, fields)
        model = BM25(index, args.k1, args.b) if name == "bm25" else TFIDF(index, normalize, log_tf)
        build_seconds = time.perf_counter() - start
        for query in list(queries.values())[:5]:
            model.search(query, 100)
        rows, cases, latencies = [], [], []
        with (folder / f"{name}_rankings.jsonl").open("w", encoding="utf-8") as output:
            for qid, query in queries.items():
                samples = []
                for _ in range(args.repeats):
                    start = time.perf_counter()
                    ranked = model.search(query, 100)
                    samples.append((time.perf_counter() - start) * 1000)
                latencies.append(float(np.median(samples)))
                scores = evaluate_ranking([doc for doc, _ in ranked], qrels[qid], METRICS)
                rows.append({"query_id": qid, **scores})
                output.write(json.dumps({"query_id": qid, "results": ranked}) + "\n")
                cases.append({"query_id": qid, "query": query, **scores, "top_results": [{"id": doc, "title": corpus[doc].get("title", ""), "grade": qrels[qid].get(doc, 0)} for doc, _ in ranked[:5]], "known_relevant_examples": [{"id": doc, "title": corpus[doc].get("title", "")} for doc, grade in qrels[qid].items() if grade > 0][:5]})
        with (folder / f"{name}_per_query.csv").open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=["query_id", *METRICS])
            writer.writeheader()
            writer.writerows(rows)
        comparisons[name] = {row["query_id"]: row["ndcg@10"] for row in rows}
        ordered = sorted(cases, key=lambda row: (row["ndcg@10"], row["query_id"]))
        write_json(folder / f"{name}_examples.json", {"worst": ordered[:5], "best": ordered[-5:]})
        summary.append({"method": name, **{metric: float(np.mean([row[metric] for row in rows])) for metric in METRICS}, "build_seconds": build_seconds, "mean_query_ms": float(np.mean(latencies)), "p95_query_ms": float(np.percentile(latencies, 95)), "fields": fields, "stopwords": stopwords, "normalize": normalize if name != "bm25" else None, "log_tf": log_tf if name != "bm25" else None})
    write_json(folder / "summary.json", summary)
    with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    with (folder / "query_comparison.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["query_id", "query", "tfidf_ndcg@10", "bm25_ndcg@10", "bm25_minus_tfidf"])
        for qid, query in queries.items():
            a, b = comparisons["tfidf"][qid], comparisons["bm25"][qid]
            writer.writerow([qid, query, a, b, b-a])
    for row in summary:
        print(f"{row['method']:24} nDCG@10={row['ndcg@10']:.4f} Recall@100={row['recall@100']:.4f} mean_ms={row['mean_query_ms']:.3f}")
    print(f"Saved results to {folder}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["download", "describe", "evaluate", "search"])
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "nfcorpus")
    parser.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    parser.add_argument("--query", default="")
    parser.add_argument("--method", choices=["tfidf", "bm25"], default="bm25")
    parser.add_argument("--k1", type=float, default=1.2)
    parser.add_argument("--b", type=float, default=0.75)
    parser.add_argument("--fields", choices=["title_text", "title", "text"], default="title_text")
    parser.add_argument("--keep-stopwords", action="store_true")
    parser.add_argument("--no-normalize", dest="normalize", action="store_false")
    parser.add_argument("--log-tf", action="store_true")
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    if args.command == "download":
        download()
    elif args.command == "describe":
        describe(args.data)
    elif args.command == "evaluate":
        evaluate(args)
    else:
        corpus = read_jsonl(args.data / "corpus.jsonl")
        index = InvertedIndex(corpus, not args.keep_stopwords, args.fields)
        model = BM25(index, args.k1, args.b) if args.method == "bm25" else TFIDF(index, args.normalize, args.log_tf)
        for doc, score in model.search(args.query):
            print(f"{score:.4f}  {doc}  {corpus[doc].get('title', '')}")


if __name__ == "__main__":
    main()
