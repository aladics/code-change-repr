from typing import List, Tuple, Union
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter, Retry
import logging
from enum import Enum
import time

import click
from gensim.models.doc2vec import Doc2Vec
import numpy as np
from urllib3 import exceptions
from gensim.corpora import Dictionary

from code_changes.cache import Cache
from flattener import (
    ChangeMethodFlattener,
    MethodDefinition,
    MethodFlattener,
    SimpleMethodFlattener,
)
from doc2vec.train import filter_document

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class MethodUnavailableException(Exception):
    pass


class MethodUnchangedException(Exception):
    pass


class IgnoreMethodException(Exception):
    pass


class SkipMethodException(Exception):
    pass


class Mode(str, Enum):
    SIMPLE_REPR = "simple"
    CHANGE_TREE_REPR = "change-tree"
    DUMP_UNCHANGED = "dump-unchanged"


def download_file(url: str, dst_path: Path):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount("http://", HTTPAdapter(max_retries=retries))
    response = session.get(url)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with dst_path.open("wb") as fp:
        for data in response.iter_content():
            fp.write(data)


def get_cached_file(
    rel_path: str, url: str, cache: Cache, is_before: bool
) -> Union[Path, None]:
    """
    Get file from cache if cached, download otherwise.
    """
    cache_path = cache.get(rel_path, is_before)
    if not cache_path.exists():
        try:
            download_file(url, cache_path)
        except (exceptions.MaxRetryError, exceptions.ConnectionError):
            return None

    return cache_path


def vectorize_flattening(
    flattened_method: List[str], doc2vec_model: Doc2Vec
) -> np.ndarray:

    doc2vec_model.random.seed(doc2vec_model.seed)  # type: ignore
    return doc2vec_model.infer_vector(flattened_method)


def append_to_results(
    before_flatten: np.ndarray, after_flatten: np.ndarray, label: str, result_path: Path
):
    with result_path.open("a") as fp:
        fp.write(",".join(f"{el:.5f}" for el in before_flatten.tolist()) + ",")
        fp.write(",".join(f"{el:.5f}" for el in after_flatten.tolist()) + ",")
        fp.write(label)
        fp.write("\n")


def parse_methods_from_csv_line(
    line: str, cache: Cache
) -> Tuple[MethodDefinition, MethodDefinition, str]:
    fields: List[str] = line.split(",")
    (
        repo,
        before_url,
        after_url,
        before_rel_file_path,
        after_rel_file_path,
        before_pos,
        after_pos,
        before_sha,
        after_sha,
        label,
    ) = (
        fields[0].strip(),
        fields[1].strip(),
        fields[2].strip(),
        fields[3].strip(),
        fields[4].strip(),
        fields[5].strip(),
        fields[6].strip(),
        fields[8].strip(),
        fields[9].strip(),
        fields[10].strip(),
    )

    before_file_path = get_cached_file(
        repo + "/" + before_sha + "/" + before_rel_file_path, before_url, cache, True
    )
    after_file_path = get_cached_file(
        repo + "/" + after_sha + "/" + after_rel_file_path, after_url, cache, False
    )

    if not before_file_path or not after_file_path:
        raise MethodUnavailableException(
            f"Before or the after path is unavailable in repo {repo}."
        )

    before_method = MethodDefinition(repo, before_sha, before_file_path, before_pos)
    after_method = MethodDefinition(repo, after_sha, after_file_path, after_pos)

    return before_method, after_method, label


def is_ignore_method(
    ignore_methods: List[str],
    before_state: MethodDefinition,
    after_state: MethodDefinition,
) -> bool:
    for method_to_ignore in ignore_methods:
        fields = method_to_ignore.split(",")
        if (
            fields[0].strip() == before_state.repo
            and fields[1].strip() == before_state.sha
            and fields[2].strip() == after_state.sha
            and fields[3].strip() == before_state.pos
            and fields[4].strip() == after_state.pos
        ):
            return True

    return False


def vectorize_method(
    method_flattener: MethodFlattener,
    label: str,
    result_path: Path,
    model: Doc2Vec,
    dictionary: Dictionary,
) -> None:

    flattened_before_method = filter_document(method_flattener.get_before(), dictionary)
    flattened_after_method = filter_document(method_flattener.get_after(), dictionary)

    if flattened_before_method == flattened_after_method:
        raise MethodUnchangedException(
            f"Before or the after flattenings are the same for a method."
        )

    vectorized_before = vectorize_flattening(flattened_before_method, model)
    vectorized_after = vectorize_flattening(flattened_after_method, model)
    append_to_results(vectorized_before, vectorized_after, label, result_path)


def get_elapsed(elapsed_secs: int) -> str:
    hours = elapsed_secs // 3600
    mins = (elapsed_secs - hours * 3600) // 60
    secs = elapsed_secs % 60

    return f"{hours:2}:{mins:2}:{secs:2}"


def dump_unchanged_method(method_flattener: MethodFlattener, result_path: Path):
    with result_path.open("a") as fp:
        fp.write(
            method_flattener.before_state.repo
            + ","
            + method_flattener.before_state.sha
            + ","
            + method_flattener.after_state.sha
            + ","
            + method_flattener.before_state.pos
            + ","
            + method_flattener.after_state.pos
            + "\n"
        )


def dump_unchanged(
    method_flattener: MethodFlattener, dictionary: Dictionary, result_path: Path
):

    flattened_before_method = filter_document(method_flattener.get_before(), dictionary)
    flattened_after_method = filter_document(method_flattener.get_after(), dictionary)

    if flattened_after_method == flattened_before_method:
        dump_unchanged_method(method_flattener, result_path)


def get_ignore_methods(ignore_methods_path: Union[str, None]) -> List[str]:
    if not ignore_methods_path:
        return []

    with Path(ignore_methods_path).open("r") as fp:
        ignore_methods = fp.readlines()

    return ignore_methods


@click.command()
@click.option(
    "--input", "src",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the CSV file containing the method changes.",
    required=True,
)
@click.option(
    "--result",
    help="Path to where the resulting flattened method changes should be stored.",
    required=True,
)
@click.option(
    "--cache-dir",
    help="Path to the directory where the files will be saved. If not set, no caching is done.",
    required=True,
)
@click.option(
    "--doc2vec-path",
    help="Path to the saved doc2vec model.",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.option(
    "--mode",
    help="The purpose for the vectorization (representation or filtered methods generating).",
    type=click.Choice(
        [Mode.SIMPLE_REPR, Mode.CHANGE_TREE_REPR, Mode.DUMP_UNCHANGED],
        case_sensitive=False,
    ),
    required=True,
)
@click.option(
    "--dict",
    "dict_path",
    help="Path to the dictionary file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.option(
    "--ignore-methods",
    "ignore_methods_path",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the file containing the methods to ignore",
    default=None,
)
@click.option(
    "--skip-n",
    help="Ignore the first n entries from the input",
    type=click.INT,
    default=0,
)
@click.option(
    "--reset/--no-reset", help="If the results file should be reset", default=False
)
def main(
    src: str,
    result: str,
    cache_dir: str,
    doc2vec_path: str,
    mode: Mode,
    dict_path: str,
    ignore_methods_path: Union[str, None],
    skip_n: int,
    reset: bool,
):
    cache = Cache(Path(cache_dir))
    result_path = Path(result)

    if result_path.exists() and reset:
        result_path.unlink()

    model: Doc2Vec = Doc2Vec.load(doc2vec_path)
    dictionary: Dictionary = Dictionary.load(dict_path)

    n_done: int = 0
    n_failed: int = 0
    n_ignored: int = 0
    n_skipped: int = 0
    n_unchanged: int = 0
    time_start = time.time()
    elapsed: int = 0
    with Path(src).open() as fp:
        header_read = False
        line = fp.readline()
        ignore_methods = get_ignore_methods(ignore_methods_path)
        while line:
            if not header_read:
                header_read = True
                line = fp.readline()
                continue

            try:
                before_method, after_method, label = parse_methods_from_csv_line(
                    line, cache
                )

                if mode == Mode.SIMPLE_REPR or mode == Mode.CHANGE_TREE_REPR:
                    if is_ignore_method(ignore_methods, before_method, after_method):
                        raise IgnoreMethodException()

                    if skip_n > n_skipped:
                        raise SkipMethodException()

                    if mode == Mode.SIMPLE_REPR:
                        method_flattener = SimpleMethodFlattener(
                            before_method,
                            after_method,
                            line_offset=-1,
                        )
                    else:
                        method_flattener = ChangeMethodFlattener(
                            before_method, after_method, line_offset=-1
                        )

                    vectorize_method(
                        method_flattener, label, result_path, model, dictionary
                    )

                elif mode == mode.DUMP_UNCHANGED:
                    method_flattener = SimpleMethodFlattener(
                        before_method,
                        after_method,
                        line_offset=-1,
                    )

                    dump_unchanged(method_flattener, dictionary, result_path)

                n_done += 1
            except MethodUnavailableException:
                n_failed += 1
            except MethodUnchangedException:
                n_unchanged += 1
            except IgnoreMethodException:
                n_ignored += 1
            except SkipMethodException:
                n_skipped += 1

            line = fp.readline()

            elapsed: int = int(time.time() - time_start)
            print(
                (f"Done methods: {n_done:5}, ignored: {n_ignored:5}, skipped: {n_skipped:5}, "
                 f"unchanged: {n_unchanged:5}, failed: {n_failed:5}, elapsed time : {get_elapsed(elapsed)}"),
                end="\r",
            )

    print(
        f"Done methods: {n_done:5}, ignored: {n_ignored:5}, skipped: {n_skipped:5}," 
        f"unchanged: {n_unchanged:5}, failed: {n_failed:5}, elapsed time : {get_elapsed(elapsed)}"
    )


if __name__ == "__main__":
    main()
