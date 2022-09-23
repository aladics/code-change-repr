from pathlib import Path
from typing import Any, List, Tuple
import click
import random

SEED = 1234
RES_HEADER = [
    "Repository",
    "Before state URL",
    "After state URL",
    "Before state file path",
    "After state file path",
    "Before state line:col",
    "After state line:col",
    "Method name",
    "Before state commit hash",
    "After state commit hash",
    "Label",
]


def add_label(dataset: List[str], label: str):
    return [f"{entry.rstrip()},{label}\n" for entry in dataset]


def sample_list(list_: List[Any], n: int) -> Tuple[List[Any], List[Any]]:
    random.seed(SEED)
    idxes = random.sample(range(0, len(list_)), n)

    return [list_[idx] for idx in idxes], [
        list_[idx] for idx in range(0, len(list_)) if idx not in idxes
    ]


def get_entires(filepath: str, label: str):
    entries = []

    with Path(filepath).open() as fp:
        while entry := fp.readline():
            entries.append(f"{entry.rstrip()},{label}\n")

    return entries


def calc_n_negatives(n_positives: int, p_n_ratio: float):
    return int(n_positives / p_n_ratio) - n_positives


def create_train_set(
    positive_file: str, n_positives: int, negative_file: str, p_n_ratio: float
) -> Tuple[List[Any], List[Any], List[Any]]:
    """
    Create train set by sampling the positive entries :param n_positives times, and sampling negative samples to keep
    the ratio given by :param p_n_ratio. Return the created train set and the leftover entries of the positive and
    negative sets.
    """
    train_set = []

    positive_entries_train, positive_entries_leftover = sample_list(
        get_entires(positive_file, "1"), n_positives
    )

    n_negatives = calc_n_negatives(n_positives, p_n_ratio)
    negative_entries_train, negative_entries_leftover = sample_list(
        get_entires(negative_file, "0"), n_negatives
    )

    negative_entries_train = [
        entry for entry in negative_entries_train if entry not in positive_entries_train
    ]
    train_set = negative_entries_train + positive_entries_train
    random.seed(SEED)
    random.shuffle(train_set)

    return train_set, positive_entries_leftover, negative_entries_leftover


def create_test_set(
    positive_leftovers: List[Any], negative_leftovers: List[Any], p_n_ratio: float
):
    """
    Create test set where the positive entries are :param positive_leftovers, and negative entries are sampled from
    the negative leftover set while keeping the ratio given by :param p_n_ratio.

    Returns the test set.
    """
    test_n_positives = len(positive_leftovers)
    test_n_negatives = calc_n_negatives(test_n_positives, p_n_ratio)
    test_negatives, _ = sample_list(negative_leftovers, test_n_negatives)

    test_negatives = [
        entry for entry in test_negatives if entry not in positive_leftovers
    ]
    test_set = test_negatives + positive_leftovers

    random.seed(SEED)
    random.shuffle(test_set)

    return test_set


def dump_data(fname: str, dataset: List[Any]) -> None:
    with Path(fname).open("w") as fp:
        fp.write(",".join(RES_HEADER) + "\n")
        for entry in dataset:
            fp.write(entry)


@click.command()
@click.option(
    "--positive-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="The file that contains the entries with positive labels.",
    required=True,
)
@click.option(
    "--negative-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="The file that contains the entries with negative labels.",
    required=True,
)
@click.option(
    "--p-n-ratio",
    type=float,
    help="The positive-negative ratio in both train and test sets.",
    default=0.2,
)
@click.option(
    "--n-positives",
    type=int,
    help="The number of positive entries in the train set, the rest will go to test set. Set to -1 if you want to "
         "keep everything in case of mode 'xval'.",
    required=True,
)
@click.option(
    "--train-fname", type=str, help="Path to the resulting train file.", default=""
)
@click.option(
    "--test-fname", type=str, help="Path to the resulting test file.", default=""
)
@click.option("--fname", type=str, help="Path to the resulting file.", default="")
@click.option(
    "--mode",
    type=click.Choice(["train-test", "xval"], case_sensitive=False),
    required=True,
)
def main(
    positive_file: str,
    negative_file: str,
    p_n_ratio: float,
    n_positives: int,
    train_fname: str,
    test_fname: str,
    fname: str,
    mode: str,
):

    if mode == "train-test":
        if not train_fname or not test_fname:
            Exception(
                "With mode 'train-test', arguments 'train-fname' and 'test-fname' must be set."
            )

        train_set, positive_leftovers, negative_leftovers = create_train_set(
            positive_file, n_positives, negative_file, p_n_ratio
        )
        dump_data(train_fname, train_set)

        test_set = create_test_set(positive_leftovers, negative_leftovers, p_n_ratio)
        dump_data(test_fname, test_set)

    elif mode == "xval":
        if not fname:
            Exception("With mode 'xval', argument 'fname' must be set.")

        if n_positives == -1:
            xval_positives = get_entires(positive_file, "1")
            n_negatives = calc_n_negatives(len(xval_positives), p_n_ratio)
            xval_negatives, _ = sample_list(get_entires(negative_file, "0"), n_negatives)
            xval_negatives = [
                entry for entry in xval_negatives if entry not in xval_positives
            ]
            xval_set = xval_positives + xval_negatives
        else:
            xval_set, _, _ = create_train_set(
                positive_file, n_positives, negative_file, p_n_ratio
            )

        random.seed(SEED)
        random.shuffle(xval_set)

        dump_data(fname, xval_set)


if __name__ == "__main__":
    main()
