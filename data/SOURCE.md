# Dataset provenance

NFCorpus: Boteva, Gholipour, Sokolov, and Riezler, “A Full-Text Learning to Rank Dataset for Medical Information Retrieval,” ECIR 2016. BEIR packaging: Thakur et al., “BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models,” NeurIPS Datasets and Benchmarks 2021.

Sources retrieved for this package:

- https://huggingface.co/datasets/BeIR/nfcorpus
- https://huggingface.co/datasets/BeIR/nfcorpus/resolve/main/corpus/corpus-00000-of-00001.parquet
- https://huggingface.co/datasets/BeIR/nfcorpus/resolve/main/queries/queries-00000-of-00001.parquet
- https://huggingface.co/datasets/BeIR/nfcorpus-qrels/resolve/main/train.tsv
- https://huggingface.co/datasets/BeIR/nfcorpus-qrels/resolve/main/dev.tsv
- https://huggingface.co/datasets/BeIR/nfcorpus-qrels/resolve/main/test.tsv

The Parquet rows were converted to JSONL without text preprocessing. Relevance TSV files were copied unchanged. The dataset card identifies the license as CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/ . Attribute the dataset creators and preserve the applicable license when redistributing data. The code license is separate.

The official BEIR ZIP endpoint returned HTTP 503 during preparation. The downloader remains available for future fresh checkouts, but the data needed to run the included experiments is already bundled.

3633 documents; 3237 query rows. There are 2590 evaluated train queries, 324 dev queries, and 323 test queries. Average combined title/text length is 245.77 tokens using the project's tokenizer before removing stopwords. Dev has 11385 judgments: 10864 grade 1 and 521 grade 2. Test has 12334 judgments: 11758 grade 1 and 576 grade 2. All 110575 supplied training judgments have grade 1. The differences between grade distributions should be recorded rather than assuming every split has the same label distribution.

Documents are titles and abstracts, not necessarily full research papers. The source is a specialized nutrition/health retrieval setting, not a representative sample of all web search. Labels depend on the dataset's collection/judgment process; unjudged documents are not guaranteed to be irrelevant.

Each experiment's settings.json stores SHA-256 hashes of the exact corpus, queries, and evaluated qrels file. Comparing methods requires the same inputs and split. Do not interpret results on data/sample as NFCorpus measurements: sample is a small fixture inherited from the supplied project.
