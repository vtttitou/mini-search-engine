from __future__ import annotations
import math
from collections.abc import Sequence

def _relevant(qrels: dict[str, int]) -> set[str]:
    return {d for d, g in qrels.items() if g > 0}

def dcg_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    return sum((max(qrels.get(doc_id, 0), 0) / math.log2(i + 2) for i, doc_id in enumerate(ranking[:k])))

def ndcg_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    ideal = sorted((g for g in qrels.values() if g > 0), reverse=True)[:k]
    ideal_dcg = sum((g / math.log2(i + 2) for i, g in enumerate(ideal)))
    return dcg_at_k(ranking, qrels, k) / ideal_dcg if ideal_dcg > 0 else 0.0

def recall_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    rel = _relevant(qrels)
    return len(rel.intersection(ranking[:k])) / len(rel) if rel else 0.0

def precision_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    rel = _relevant(qrels)
    return len(rel.intersection(ranking[:k])) / k if k else 0.0

def average_precision_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    rel = _relevant(qrels)
    if not rel:
        return 0.0
    hits, total = (0, 0.0)
    for i, doc_id in enumerate(ranking[:k], start=1):
        if doc_id in rel:
            hits += 1
            total += hits / i
    return total / len(rel)

def reciprocal_rank_at_k(ranking: Sequence[str], qrels: dict[str, int], k: int) -> float:
    rel = _relevant(qrels)
    for i, doc_id in enumerate(ranking[:k], start=1):
        if doc_id in rel:
            return 1.0 / i
    return 0.0
METRICS = {'ndcg': ndcg_at_k, 'recall': recall_at_k, 'precision': precision_at_k, 'map': average_precision_at_k, 'mrr': reciprocal_rank_at_k}

def parse_metric(name: str):
    try:
        base, k = name.lower().split('@')
        return (METRICS[base], int(k))
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Bad metric {name!r}. Use one of {sorted(METRICS)} as 'name@k', e.g. 'ndcg@10'.") from exc

def evaluate_ranking(ranking: Sequence[str], qrels: dict[str, int], metrics: Sequence[str]) -> dict[str, float]:
    out = {}
    for name in metrics:
        fn, k = parse_metric(name)
        out[name] = fn(ranking, qrels, k)
    return out
