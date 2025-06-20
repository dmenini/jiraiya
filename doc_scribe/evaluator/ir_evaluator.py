from collections import defaultdict

import numpy as np

from doc_scribe.domain.eval import Metrics, Prediction


class InformationRetrievalEvaluator:
    def __init__(
        self,
        relevant_docs: dict[str, list[str]],  # qid => list[cid]
        mrr_at_k: list[int] | None = None,
        ndcg_at_k: list[int] | None = None,
        accuracy_at_k: list[int] | None = None,
        precision_recall_at_k: list[int] | None = None,
        map_at_k: list[int] | None = None,
    ):
        self.relevant_docs = {cid: list(set(qid)) for cid, qid in relevant_docs.items()}

        self.mrr_at_k = mrr_at_k or [10]
        self.ndcg_at_k = ndcg_at_k or [10]
        self.accuracy_at_k = accuracy_at_k or [1, 3, 5, 10]
        self.precision_recall_at_k = precision_recall_at_k or [1, 3, 5, 10]
        self.map_at_k = map_at_k or [100]

    def compute_metrics(self, predictions: dict[str, list[Prediction]]) -> Metrics:
        # predictions: {qid -> [{cid -> abc, score -> 0.9}]}

        # Init score computation values
        num_hits_at_k: dict[int, list] = defaultdict(list)
        precision_at_k: dict[int, list] = defaultdict(list)
        recall_at_k: dict[int, list] = defaultdict(list)
        mrr_at_k: dict[int, list] = defaultdict(list)
        ndcg_at_k: dict[int, list] = defaultdict(list)
        map_at_k: dict[int, list] = defaultdict(list)

        # Compute metrics on results
        for query_id, pred in predictions.items():
            sorted_hits = sorted(pred, key=lambda hit: hit.score, reverse=True)
            top_hits: list[str] = [hit.cid for hit in sorted_hits]
            relevant_docs: list[str] = self.relevant_docs[query_id]

            for k in self.accuracy_at_k:
                hits = self._compute_hits(top_hits[:k], relevant_docs)
                num_hits_at_k[k].append(hits)

            for k in self.precision_recall_at_k:
                precision = self._compute_precision(top_hits[:k], relevant_docs)
                precision_at_k[k].append(precision)

            for k in self.precision_recall_at_k:
                recall = self._compute_recall(top_hits[:k], relevant_docs)
                recall_at_k[k].append(recall)

            for k in self.mrr_at_k:
                mrr = self._compute_mrr(top_hits[:k], relevant_docs)
                mrr_at_k[k].append(mrr)

            for k in self.ndcg_at_k:
                ndcg = self._compute_ndcg(top_hits[:k], relevant_docs)
                ndcg_at_k[k].append(ndcg)

            for k in self.map_at_k:
                map_ = self._compute_map(top_hits[:k], relevant_docs)
                map_at_k[k].append(map_)

        return Metrics(
            support=len(predictions),
            accuracy=self._mean(num_hits_at_k),
            precision=self._mean(precision_at_k),
            recall=self._mean(recall_at_k),
            ndcg=self._mean(ndcg_at_k),
            mrr=self._mean(mrr_at_k),
            map=self._mean(map_at_k),
        )

    def _compute_hits(self, top_hits: list[str], relevant_docs: list[str]) -> int:
        return int(any(hit in relevant_docs for hit in set(top_hits)))

    def _compute_precision(self, top_hits: list[str], relevant_docs: list[str]) -> float:
        num_correct = sum(hit in relevant_docs for hit in set(top_hits))
        return num_correct / len(top_hits)

    def _compute_recall(self, top_hits: list[str], relevant_docs: list[str]) -> float:
        num_correct = sum(hit in relevant_docs for hit in set(top_hits))
        recall = num_correct / len(relevant_docs)
        return recall

    def _compute_mrr(self, top_hits: list[str], relevant_docs: list[str]) -> float:
        for rank, hit in enumerate(top_hits):
            if hit in relevant_docs:
                return 1.0 / (rank + 1)
        return 0.0

    def _compute_ndcg(self, top_hits: list[str], relevant_docs: list[str]) -> float:
        predicted = [1 if hit in relevant_docs else 0 for hit in top_hits]
        predicted_relevance = sum(predicted[i] / np.log2(i + 2) for i in range(len(predicted)))
        true_relevance = sum(1 / np.log2(i + 2) for i in range(len(predicted)))
        ndcg = predicted_relevance / true_relevance if true_relevance != 0 else 0.0
        return ndcg

    def _compute_map(self, top_hits: list[str], relevant_docs: list[str]) -> float:
        num_correct = 0
        sum_precisions = 0.0
        for rank, hit in enumerate(top_hits):
            if hit in relevant_docs:
                num_correct += 1
                sum_precisions += num_correct / (rank + 1)
        avg_precision = sum_precisions / num_correct if num_correct else 0.0
        return avg_precision

    def _mean(self, metric_at_k: dict[int, list]) -> dict[int, float]:
        return {k: float(np.mean(metric_at_k[k])) for k, v in metric_at_k.items()}
