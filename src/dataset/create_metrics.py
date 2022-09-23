from typing import List
from pathlib import Path
from csv import DictReader
from shutil import copy
from subprocess import run
import subprocess
from os import remove

import click
from tqdm import tqdm

from util.models import ChangedMethodEntry, MethodDefinition
from code_changes.cache import Cache
from conf.config import get as get_config
from conf.config import Config, ConfigException

# Config related to the methods.csv generated by SM
METHOD_LINE_FIELD_NAME = 'Line'
METRICS_START_IDX = 10
METRICS_END_IDX = 46

# Config related to the SM directory hierarch
INPUT_SUBDIR = "input"
OUTPUT_SUBDIR = "results"
PROJECT_ID = "placeholder"


class MetricsFileException(Exception):
    pass


def run_sm_linux(sm_base_dir: str, project_id: str):
    """
    Run SM natively on linux.
    """

    run(["./sm_analyzer.sh", f"-projectName={project_id}", "-projectBaseDir=input", "-resultsDir=results"],
        cwd=sm_base_dir, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def run_sm_os_independently(sm_base_dir: str, project_id: str):
    """
    Run SM using docker. Build the image manually before using this!
    """
    run(["docker-compose", "run", "-e", f"PROJECT_ID={project_id}", "sourcemeter"], cwd=sm_base_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def reset_dir(directory: Path) -> None:
    """
    Delete the contents of a directory
    """

    for content in directory.rglob("*"):
        if content.is_file():
            remove(content)


def run_sm(filepath: Path) -> None:
    """
    Run SourceMeter for a Java file
    """

    config: Config = get_config()
    input_path = config.sourcemeter.path / INPUT_SUBDIR
    sm_base_dir = str(config.sourcemeter.path.resolve())
    filepath_str = str(filepath.resolve())
    input_path_str = str(input_path.resolve())

    reset_dir(input_path)
    copy(filepath_str, input_path_str)

    os = config.sourcemeter.os.lower()
    match os:
        case "independent":
            run_sm_os_independently(sm_base_dir=sm_base_dir, project_id=PROJECT_ID)
        case "windows":
            raise NotImplementedError("Windows SM runner is not implemented.")
        case "linux":
            run_sm_linux(sm_base_dir=sm_base_dir, project_id=PROJECT_ID)
        case _:
            raise ConfigException(f"Unknown config param for 'os': '{os}'")


def get_metrics_csv(sm_result_dir: Path, project_id: str) -> Path:
    """
    Find the CSV containing the (method level) metrics in the SM result directory.
    """

    metrics_methods = list((sm_result_dir / project_id).rglob(f"{project_id}-Method.csv"))
    if len(metrics_methods) == 0:
        raise MetricsFileException("No metrics file found")
    elif len(metrics_methods) > 1:
        raise MetricsFileException("More than one metrics file found")

    return metrics_methods[0]


def get_metrics_from_csv(metrics_csv_path: Path, method: MethodDefinition) -> List[str]:
    """
    Fetch the metrics corresponding to a method from a metrics CSV.
    """

    with metrics_csv_path.open() as csv_file:
        reader = DictReader(csv_file)
        for row in reader:
            if not int(row[METHOD_LINE_FIELD_NAME]) == method.line:
                continue

            return list(row.values())[METRICS_START_IDX:METRICS_END_IDX + 1]


def get_sm_metrics(method: MethodDefinition) -> List[str]:
    """
    Fetch the metrics for a method.
    """

    run_sm(method.filepath)

    result_dir_path = get_config().sourcemeter.path / OUTPUT_SUBDIR
    metrics_csv_path: Path = get_metrics_csv(result_dir_path, PROJECT_ID)
    return get_metrics_from_csv(metrics_csv_path, method)


def get_concatenated_metrics(ch_method: ChangedMethodEntry):
    """
    Fetch the metrics for both before and after states of the changed method, return them concatenated
    """

    before_metrics: List[str] = get_sm_metrics(ch_method.before_state)
    after_metrics: List[str] = get_sm_metrics(ch_method.after_state)
    return before_metrics + after_metrics


def get_result_header() -> List[str]:
    header = []
    header += [f"feature_{field_n}" for field_n in range(0, (METRICS_END_IDX-METRICS_START_IDX+1)*2)]
    header += ["label"]

    return header


def init_result(result_path: Path, reinit: bool) -> None:
    if reinit and result_path.exists():
        result_path.unlink()

    if not result_path.exists():
        with result_path.open("w") as fp:
            fp.write(",".join(get_result_header()) + "\n")


def append_to_results(metrics: List[str], label: int, result_path):
    with result_path.open("a") as fp:
        fp.write(",".join(metrics + [str(label)]) + "\n")


def get_n_lines(path: Path):
    fp = open(path)
    n_lines = sum(1 for _ in fp)
    fp.close()

    return n_lines


@click.command()
@click.option("--src", type=click.Path(dir_okay=False, exists=True, readable=True), help="The source CSV file.",
              required=True)
@click.option("--cache-dir", type=click.Path(file_okay=False, exists=True, readable=True),
              help="The directory containing the cache.", required=True)
@click.option("--result", "result_path_str",  type=click.Path(), help="Path to the result csv", required=True)
@click.option("--reinit/--no-reinit", default=False, help="Set if results should be reinitialized.")
def main(src: str, cache_dir: str, result_path_str: str, reinit: bool):
    result_path = Path(result_path_str)
    src_path = Path(src)
    init_result(result_path, reinit)

    cache = Cache(Path(cache_dir))
    is_header_read: bool = False
    n_lines = get_n_lines(src_path)

    with src_path.open("r") as fp:
        with tqdm(total=n_lines) as pbar:
            while line := fp.readline():
                if not is_header_read:
                    is_header_read = True
                    continue

                ch_method: ChangedMethodEntry = ChangedMethodEntry.from_csv_line(line, cache)
                ch_metrics: List[str] = get_concatenated_metrics(ch_method)
                append_to_results(ch_metrics, ch_method.label, result_path)
                pbar.update(1)


if __name__ == '__main__':
    main()
