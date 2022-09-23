from dataclasses import dataclass
from pathlib import Path
from typing import Union
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib3 import exceptions


@dataclass
class Cache:
    cache_path: Path
    before_cache_rel_path: str = "before"
    after_cache_rel_path: str = "after"

    @staticmethod
    def download_file(url: str, dst_path: Path):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        session.mount("http://", HTTPAdapter(max_retries=retries))
        response = session.get(url)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with dst_path.open("wb") as fp:
            for data in response.iter_content():
                fp.write(data)

    @staticmethod
    def get_rel_path(repo: str, sha: str, path: str):
        return repo + "/" + sha + "/" + path

    @property
    def before_path(self) -> Path:
        return self.cache_path / self.before_cache_rel_path

    @property
    def after_path(self) -> Path:
        return self.cache_path / self.after_cache_rel_path

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

    def get_or_download(self,  rel_path: str, url: str, is_before: bool) -> Union[Path, None]:
        """
        Get file from cache if cached, download otherwise.
        """
        cache_path = self.get(rel_path, is_before)
        if not cache_path.exists():
            try:
                Cache.download_file(url, cache_path)
            except (exceptions.MaxRetryError, exceptions.ConnectionError):
                return None

        return cache_path
