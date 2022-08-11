from pathlib import Path
import sys
from typing import Dict, Union

DBH_PATH = "F:/work/kutatas/dwf/dwf_now/DeepWaterFramework/DeepBugHunter"
SHARED_PARAMS = {
    "label": "label",
    "resample": "up",
    "resample_amount": 50,
    "seed": 1337,
    "output": "output",
    "clean": False,
    "calc_completeness": True,
    "preprocess": [
        # [
        #    'features',
        #    'standardize'
        # ],
        ["labels", "binarize"]
    ],
    "return_results": True,
}

MODEL_PARAMS: Dict[str, Dict[str, Union[str, int]]] = {
    "linear": {},
    "forest": {"n_estimators": 100, "max_depth": 7, "criterion": "entropy"},
}

import click


def set_dbh_path() -> None:
    dbh_path_str = DBH_PATH

    if not Path(dbh_path_str).exists():
        raise ValueError(f"Invalid DBH Path, set it accordingly in model_runner.py")

    sys.path.append(str(Path(dbh_path_str).resolve()))


from dbh_api.res.runner import TaskFactory, run_xval


@click.command()
@click.option(
    "--input", "input_path", type=click.Path(exists=True, dir_okay=False), required=True
)
def main(input_path: str):
    factory = TaskFactory(shared_params=SHARED_PARAMS)

    results = []
    for model_name, params in MODEL_PARAMS.items():
        task = factory.get(model_name, params)
        run_xval(task, Path(input_path), results)

    print(results)


if __name__ == "__main__":
    main()
