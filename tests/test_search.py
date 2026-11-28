import math
import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from engine.index import InvertedIndex
from engine.tfidf import TFIDF
from engine.bm25 import BM25
from engine.text import tokenize
from engine.metrics import evaluate_ranking
from engine.data import ROOT, load_data

DOCS = {"a": {"text": "apple apple banana"}, "b": {"text": "banana cherry"}, "c": {"text": "pear"}}


@pytest.mark.parametrize("log_tf", [False, True])
def test_cosine_matches_reference(log_tf):
    model = TFIDF(InvertedIndex(DOCS), log_tf=log_tf)
    vectorizer = TfidfVectorizer(analyzer=tokenize, sublinear_tf=log_tf)
    matrix = vectorizer.fit_transform([d["text"] for d in DOCS.values()])
    reference = (vectorizer.transform(["apple banana banana"]) @ matrix.T).toarray()[0]
    actual = dict(model.search("apple banana banana"))
    for i, key in enumerate(DOCS):
        assert actual.get(key, 0) == pytest.approx(reference[i])


def test_bm25_matches_hand_calculation():
    index = InvertedIndex({k: DOCS[k] for k in ("a", "b")})
    score = BM25(index).search("apple")[0][1]
    expected = math.log(2) * 2 * 2.2 / (2 + 1.2 * (0.25 + 0.75 * 3 / 2.5))
    assert score == pytest.approx(expected)


@pytest.mark.parametrize("method", [TFIDF, BM25])
def test_edges_and_ties(method):
    index = InvertedIndex({str(i): {"text": "apple"} for i in range(100)})
    model = method(index)
    assert [doc for doc, _ in model.search("apple", 3)] == ["0", "1", "2"]
    assert model.search("unknown") == []
    assert model.search("the and") == []
    assert model.search("apple", 0) == []
    assert method(InvertedIndex({"empty": {"text": ""}})).search("apple") == []


def test_metrics():
    result = evaluate_ranking(["a", "b", "c", "d"], {"b": 2, "d": 1, "z": 1}, ["ndcg@4", "recall@4", "precision@4", "map@4", "mrr@4"])
    assert result["recall@4"] == pytest.approx(2/3)
    assert result["precision@4"] == .5
    assert result["map@4"] == pytest.approx(1/3)
    assert result["mrr@4"] == .5
    assert result["ndcg@4"] == pytest.approx((2/math.log2(3) + 1/math.log2(5))/(2 + 1/math.log2(3) + .5))


def test_fixture_integrity():
    corpus, queries, qrels = load_data(ROOT / "data/sample", "test")
    assert len(corpus) == 14 and len(queries) == 3
    assert qrels["PLAIN-5"]["MED-13"] == 2


def test_length_and_tf_effects():
    index = InvertedIndex({"short": {"text": "apple"}, "long": {"text": "apple filler filler"}})
    assert TFIDF(index).search("apple")[0][0] == "short"
    scores = dict(TFIDF(index, normalize=False).search("apple"))
    assert scores["short"] == scores["long"]
    scores = dict(BM25(index, b=0).search("apple"))
    assert scores["short"] == scores["long"]


@pytest.mark.parametrize("method", [TFIDF, BM25])
def test_multiword_topk_matches_full_sort(method):
    documents = {str(i): {"text": "apple " * (i % 4) + "banana " * (i % 7) + "pear " * (i % 3)} for i in range(200)}
    index = InvertedIndex(documents)
    model = method(index)
    full = model.search("apple banana", 200)
    assert model.search("apple banana", 7) == full[:7]
    assert model.search("apple apple banana", 7) == model.search("apple apple banana", 200)[:7]


def test_experiment_outputs(tmp_path, monkeypatch):
    import argparse
    import json
    import experiment
    monkeypatch.setattr(experiment, "ROOT", tmp_path)
    args = argparse.Namespace(data=ROOT / "data/sample", split="dev", ablation=False, fields="title_text", keep_stopwords=False, normalize=True, log_tf=False, k1=1.2, b=0.75, repeats=1)
    experiment.evaluate(args)
    folder = next((tmp_path / "results").iterdir())
    scores = json.loads((folder / "summary.json").read_text())
    assert {row["method"] for row in scores} == {"tfidf", "bm25"}
    assert all(0 <= row["ndcg@10"] <= 1 for row in scores)
    assert (folder / "query_comparison.csv").exists()
    assert len(json.loads((folder / "settings.json").read_text())["hashes"]) == 3
