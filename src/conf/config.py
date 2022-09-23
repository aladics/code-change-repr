from pathlib import Path
from typing import List, Union, Dict
from pydantic import BaseModel
import yaml

CONFIG_PATH = Path(__file__).parent.resolve() / 'config.yaml'


class ConfigException(Exception):
    pass


class SourceMeter(BaseModel):
    path: Path
    os: str


class Hyper(BaseModel):
    search_params_path: Path
    n_candidates: int


class Config(BaseModel):
    model_names: List[str]
    hyper: Hyper
    sourcemeter: SourceMeter
    shared_params: Dict[str, Union[str, int, bool]] = {
        "label": "label",
        "resample": "up",
        "resample_amount": 50,
        "seed": 1337,
        "output": "output",
        "clean": False,
        "calc_completeness": True,
        "preprocess": [
            ["features", "standardize"],
            ["labels", "binarize"]
        ],
        "return_results": True,
    }


def get() -> Config:
    with CONFIG_PATH.open() as fp:
        yaml_conf = yaml.safe_load(fp)

    config = Config(**yaml_conf)
    return config


if __name__ == '__main__':
    get()
