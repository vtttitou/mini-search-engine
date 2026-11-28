from collections import Counter
import numpy as np
from scipy.sparse import csr_matrix
from engine.text import tokenize


class InvertedIndex:
    def __init__(self, documents, remove_stopwords=True, fields="title_text"):
        if not documents:
            raise ValueError("The document collection is empty")
        if fields not in ("title_text", "title", "text"):
            raise ValueError("Unknown field selection")
        self.documents = documents
        self.ids = list(documents)
        self.remove_stopwords = remove_stopwords
        self.vocabulary = {}
        rows, columns, frequencies = [], [], []
        lengths = []
        for column, doc_id in enumerate(self.ids):
            doc = documents[doc_id]
            text = (doc.get("title", "") + " " + doc.get("text", "")) if fields == "title_text" else doc.get(fields, "")
            counts = Counter(tokenize(text, remove_stopwords))
            lengths.append(sum(counts.values()))
            for term, frequency in counts.items():
                row = self.vocabulary.setdefault(term, len(self.vocabulary))
                rows.append(row)
                columns.append(column)
                frequencies.append(frequency)
        self.counts = csr_matrix((frequencies, (rows, columns)), shape=(len(self.vocabulary), len(self.ids)), dtype=np.float64)
        self.lengths = np.asarray(lengths, dtype=float)
        self.df = np.diff(self.counts.indptr)
        self.size = len(self.ids)

    def query_counts(self, text):
        return {self.vocabulary[word]: count for word, count in Counter(tokenize(text, self.remove_stopwords)).items() if word in self.vocabulary}

    def rank(self, weights, query, k):
        if k < 1 or not query:
            return []
        if len(query) == 1:
            term, weight = next(iter(query.items()))
            start, end = weights.indptr[term:term + 2]
            ids = weights.indices[start:end]
            values = weights.data[start:end] * weight
        else:
            scores = np.zeros(self.size)
            for term, weight in query.items():
                start, end = weights.indptr[term:term + 2]
                scores[weights.indices[start:end]] += weight * weights.data[start:end]
            ids = np.flatnonzero(scores > 0)
            values = scores[ids]
        if len(values) > k:
            threshold = -np.partition(-values, k - 1)[k - 1]
            better = np.flatnonzero(values > threshold)
            tied = np.flatnonzero(values == threshold)
            needed = k - len(better)
            if len(tied) > needed:
                tied = tied[np.argpartition(ids[tied], needed - 1)[:needed]]
            selected = np.concatenate((better, tied))
            ids, values = ids[selected], values[selected]
        order = np.lexsort((ids, -values))[:k]
        return [(self.ids[ids[i]], float(values[i])) for i in order]
