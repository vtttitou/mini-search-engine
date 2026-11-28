import numpy as np
from engine.index import InvertedIndex


class BM25:
    def __init__(self, index: InvertedIndex, k1=1.2, b=0.75):
        if k1 < 0 or not 0 <= b <= 1:
            raise ValueError("Require k1 >= 0 and 0 <= b <= 1")
        self.index = index
        weights = index.counts.copy()
        idf = np.log1p((index.size - index.df + 0.5) / (index.df + 0.5))
        average_length = index.lengths.mean() or 1
        length_factor = 1 - b + b * index.lengths[weights.indices] / average_length
        weights.data = np.repeat(idf, index.df) * weights.data * (k1 + 1) / (weights.data + k1 * length_factor)
        self.weights = weights

    def search(self, query, k=10):
        return self.index.rank(self.weights, self.index.query_counts(query), k)
