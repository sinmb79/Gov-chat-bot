from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    text: str
    doc_id: str
    score: float
    metadata: dict = field(default_factory=dict)
