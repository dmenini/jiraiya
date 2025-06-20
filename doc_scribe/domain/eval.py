from pydantic import BaseModel


class Metrics(BaseModel):
    support: int
    accuracy: dict[int, float]
    precision: dict[int, float]
    recall: dict[int, float]
    ndcg: dict[int, float]
    mrr: dict[int, float]
    map: dict[int, float]

    def __str__(self) -> str:
        messages = [f"support: {self.support}"]
        for name, metric_at_k in self.model_dump(exclude={"support"}).items():
            for k, metric in metric_at_k.items():
                messages.append(f"{name}@{k}: {metric:.4f}")
        return "\n".join(messages)


class Prediction(BaseModel):
    id: str
    cid: str
    score: float
    text: str


class Datapoint(BaseModel):
    id: str
    qid: str
    query: str
    cid: list[str]
    corpus: list[str]
    language: str
    title: list[str]
    ground_truth: str | None = None
