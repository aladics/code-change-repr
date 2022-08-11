"""
Create a dictionary from a CSV file, words are separated by commas.
"""

from pathlib import Path
import logging

from gensim.corpora import Dictionary
import click

NO_BELOW_PERCENT = 0.01
NO_ABOVE_PERCENT = 1
KEEP_N_MOST_COMMON = 500
CORPUS_APPROX_SIZE = 2_000_000

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False


class MFileHandler(logging.StreamHandler):
    """Handler that controls the writing of the newline character"""

    special_code = "[r!]"

    def emit(self, record) -> None:

        if self.special_code in record.msg:
            record.msg = record.msg.replace(self.special_code, "")
            self.terminator = "\r"
        else:
            self.terminator = "\n"

        return super().emit(record)


handler = MFileHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    fmt="[%(levelname)s | %(asctime)s] %(message)s", datefmt="%Y/%d/%m %H:%M"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def remove_extremes(dictionary: Dictionary):
    logger.info(
        f"Removing tokens that are not present in at least {round(dictionary.num_docs * NO_BELOW_PERCENT)} ({NO_BELOW_PERCENT * 100}% of total documents) documents, and are present at most {NO_ABOVE_PERCENT*100}% of the documents."
    )
    dictionary.filter_extremes(
        no_below=round(dictionary.num_docs * NO_BELOW_PERCENT),
        no_above=NO_ABOVE_PERCENT,
        keep_n=KEEP_N_MOST_COMMON,
    )


def preprocess_csv_line(csv_line: str) -> list[str]:
    return [word.lower().strip() for word in csv_line.split(",")]


@click.command()
@click.option(
    "--corpus",
    help="Path to the input corpus that's going to be processed.",
    type=click.Path(exists=True, file_okay=True, readable=True),
)
@click.option(
    "--save-fname",
    type=str,
    help="Path to the file where the dictionary object should be saved.",
    required=True,
)
def main(corpus: str, save_fname: str):
    corpus_path = Path(corpus)

    dictionary = Dictionary()
    logger.info("Started corpus processing, dictionary constructed.")
    with corpus_path.open() as fp:
        docs_done = 0
        while line := fp.readline():
            processed_line = preprocess_csv_line(line)
            dictionary.add_documents(documents=[processed_line], prune_at=None)  # type: ignore
            docs_done += 1
            logger.info(
                f"Documents added: {docs_done:6} [{docs_done / CORPUS_APPROX_SIZE * 100:.2f}%][r!]"
            )

    logger.info(
        f"Dictionary is created with {dictionary.num_docs} documents (methods) processed and has {len(dictionary)} unique words (tokens)."
    )

    remove_extremes(dictionary)

    logger.info(f"Final dictionary has {len(dictionary)} unique words (tokens).")
    dictionary.save(save_fname)


if __name__ == "__main__":
    main()
