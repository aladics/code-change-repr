from typing import Dict, Any, List, Union, Tuple

from dbh_api.res.hyper import get_randomized_params
from dbh_api.res.runner import TaskFactory, run_xval
from conf.config import get as get_config
from conf.config import Config
from eval.metrics import Metrics

import click
from pathlib import Path
import yaml
from tqdm import tqdm


def run_all_candidates(model_name: str, params_candidates: Dict[str, Any],
                       factory: TaskFactory, xval_path: Path) -> Tuple[Metrics, str, List[Metrics]]:
    best_metrics: Union[Metrics, None] = None
    best_params: Union[str, None] = None
    all_metrics: List[Metrics] = []
    for params_candidate in params_candidates:
        task = factory.get(model_name, params_candidate)
        res = run_xval(task, xval_path)
        test_results = res['test']

        result_metrics = Metrics(test_results['fmes'], test_results['precision'], test_results['recall'])
        all_metrics.append(result_metrics)
        if not best_metrics or result_metrics.fmes > best_metrics.fmes:
            best_metrics = result_metrics
            best_params = res['strategy']

    return best_metrics, best_params, all_metrics


@click.command()
@click.option("--xval-path", "xval_path_", type=click.Path(exists=True, dir_okay=False, readable=True), required=True)
@click.option("--result", required=True, type=click.Path())
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
        best_metrics, best_params, all_metrics = run_all_candidates(model_name, params_candidates, factory, xval_path)
        results[model_name] = {}
        results[model_name]['best_metrics'] = best_metrics.to_dict()
        results[model_name]['best_params'] = best_params
        results[model_name]['all_metrics'] = [metrics.to_dict() for metrics in all_metrics]

        with result_path.open("w") as fp:
            yaml.dump(results, fp, default_flow_style=False)


if __name__ == '__main__':
    search()
