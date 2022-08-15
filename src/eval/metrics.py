from typing import Dict

from dataclasses import dataclass
from numpy import ndarray

@dataclass
class Metrics:
    fmes: ndarray
    precision: ndarray
    recall: ndarray

    def to_dict(self) -> Dict[str, float]:
        return dict(fmes=self.fmes.item(), precision=self.precision.item(), recall=self.recall.item())
