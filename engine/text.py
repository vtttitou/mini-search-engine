import re
import unicodedata

STOPWORDS = frozenset('a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it its itself just me more most my no nor not of off on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your'.split())


def tokenize(text, remove_stopwords=True):
    text = unicodedata.normalize("NFKC", text).lower()
    words = re.findall(r"[a-z0-9]+", text)
    return [word for word in words if word not in STOPWORDS] if remove_stopwords else words
