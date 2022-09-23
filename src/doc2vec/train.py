from pathlib import Path
import logging
from typing import List

import click
from gensim.corpora import Dictionary
from gensim.models import doc2vec

from src.doc2vec.create_dictionary import preprocess_csv_line


def filter_document(document: List[str], dictionary: Dictionary) -> List[str]:
    filtered_doc = dictionary.doc2idx(document=document, unknown_word_index=-1)
    filtered_doc = [
        dictionary.get(id) if id != -1 else "OOV_TOKEN" for id in filtered_doc
    ]

    return filtered_doc  # type: ignore


class Corpus:
    """Corpus created from a csv file, words are separated by commas, filtered using a dictionary prepared on the
    same file. """

    def filter_document(self, document: List[str]) -> List[str]:
        filtered_doc = self.dictionary.doc2idx(document=document, unknown_word_index=-1)
        filtered_doc = [
            self.dictionary.get(id) if id != -1 else "OOV_TOKEN" for id in filtered_doc
        ]

        return filtered_doc  # type: ignore

    def preprocess_document(self, line: str) -> List[str]:
        document = preprocess_csv_line(line)
        document = self.filter_document(document)

        return document

    def __init__(self, corpus_path: str, dictonary: Dictionary):
        self.corpus = Path(corpus_path)
        self.dictionary = dictonary

    def __iter__(self):
        with self.corpus.open() as fp:
            for i, line in enumerate(fp):
                tokens = self.preprocess_document(line)

                yield doc2vec.TaggedDocument(tokens, [i])


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s | %(asctime)s] %(message)s",
    datefmt="%Y/%d/%m %H:%M",
)


@click.command()
@click.option(
    "--dictionary",
    "dictionary_path",
    type=click.Path(exists=True, dir_okay=False),
    help="The dictionary the we are going ",
)
@click.option(
    "--corpus",
    "corpus_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="The path to the corpus from what we train doc2vec.",
)
@click.option(
    "--save-fname",
    help="Path to the file where the trained doc2vec model should be saved.",
)
def main(dictionary_path: str, corpus_path: str, save_fname: str):
    dictionary: Dictionary = Dictionary.load(dictionary_path)
    model = doc2vec.Doc2Vec(vector_size=100, epochs=40)
    corpus = Corpus(corpus_path, dictionary)
    model.build_vocab(corpus)
    model.train(
        corpus,
        total_examples=model.corpus_count,
        epochs=model.epochs,
    )
    model.save(save_fname)


if __name__ == "__main__":
    main()
