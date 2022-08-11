from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Union


@dataclass
class Cache:
    cache_path: Path
    before_cache_rel_path: str = "before"
    after_cache__rel_path: str = "after"

    @property
    def before_path(self) -> Path:
        return self.cache_path / self.before_cache_rel_path

    @property
    def after_path(self) -> Path:
        return self.cache_path / self.after_cache__rel_path

    def __post_init__(self):
        cache_path = Path(self.cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)

        self.before_path.mkdir(parents=True, exist_ok=True)
        self.after_path.mkdir(parents=True, exist_ok=True)

    def get(self, relative_path: str, before: bool) -> Path:
        if before:
            cache_path = self.before_path
        else:
            cache_path = self.after_path

        return cache_path / relative_path
