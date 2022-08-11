from typing import Dict, Any, List, Union, Tuple

from dbh_api.res.hyper import get_randomized_params
from dbh_api.res.runner import TaskFactory, run_xval
from conf.config import get as get_config
from conf.config import Config

import click
from pathlib import Path
import yaml
from tqdm import tqdm

def run_all_candidates(model_name: str, params_candidates: Dict[str, Any],
                       factory: TaskFactory, xval_path: Path) -> Tuple[float, str, List[float]]:
    best_fmes: Union[float, None] = None
    best_params: Union[str, None] = None
    fmes_values: List[float] = []
    for params_candidate in params_candidates:
        task = factory.get(model_name, params_candidate)
        res = run_xval(task, xval_path)

        fmes: float = res['test']['fmes']
        fmes_values.append(fmes)
        if not best_fmes or fmes > best_fmes:
            best_fmes = fmes
            best_params = res['strategy']
        continue

    return best_fmes, best_params, fmes_values


@click.command()
@click.option("--xval-path", "xval_path_", type=click.Path(exists=True, dir_okay=False, readable=True), required=True)
@click.option("--result", required=True)
def search(xval_path_: str, result: str):
    xval_path = Path(xval_path_)
    result_path = Path(result)
    config: Config = get_config()

    results = {}
    for model_name in tqdm(config.model_names):
        if model_name == 'linear':
            continue

        params_candidates = get_randomized_params(model_name, config.hyper.search_params_path,
                                                  config.hyper.n_candidates)
        factory: TaskFactory = TaskFactory(config.shared_params)
        best_fmes, best_params, all_fmes = run_all_candidates(model_name, params_candidates, factory, xval_path)
        results[model_name] = {}
        results[model_name]['best_fmes'] = best_fmes.item()
        results[model_name]['best_params'] = best_params
        results[model_name]['all_fmes'] = [el.item() for el in all_fmes]

        with result_path.open("w") as fp:
            yaml.dump(results, fp, default_flow_style=False)


if __name__ == '__main__':
    search()
