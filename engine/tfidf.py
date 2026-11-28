import numpy as np
from engine.index import InvertedIndex


class TFIDF:
    def __init__(self, index: InvertedIndex, normalize=True, log_tf=False):
        self.index = index
        self.normalize = normalize
        self.log_tf = log_tf
        self.idf = np.log((index.size + 1) / (index.df + 1)) + 1
        weights = index.counts.copy()
        if log_tf:
            weights.data = 1 + np.log(weights.data)
        weights.data *= np.repeat(self.idf, index.df)
        if normalize:
            norms = np.sqrt(np.asarray(weights.power(2).sum(axis=0)).ravel())
            norms[norms == 0] = 1
            weights.data /= norms[weights.indices]
        self.weights = weights

    def search(self, query, k=10):
        counts = self.index.query_counts(query)
        vector = {term: (1 + np.log(count) if self.log_tf else count) * self.idf[term] for term, count in counts.items()}
        if self.normalize and vector:
            norm = np.sqrt(sum(value * value for value in vector.values()))
            vector = {term: value / norm for term, value in vector.items()}
        return self.index.rank(self.weights, vector, k)
