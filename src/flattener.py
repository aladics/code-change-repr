from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List, Union
from pathlib import Path
import logging
import glob

import click

from tree import TreeSitterTree, get_sitter_AST
from change_tree import ChangeTree
from util.models import MethodDefinition

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s | %(asctime)s] %(message)s",
    datefmt="%Y/%d/%m %H:%M",
)


@dataclass
class MethodFlattener(ABC):
    before_state: MethodDefinition
    after_state: MethodDefinition
    line_offset: int = 0
    col_offset: int = 0

    @abstractmethod
    def get_before(self) -> List[str]:
        pass

    @abstractmethod
    def get_after(self) -> List[str]:
        pass

    def get_flatten(self, tree: Union[TreeSitterTree, ChangeTree]) -> List[str]:
        """Flatten the input tree by doing a BFS."""
        flattened: list[str] = []
        for node in tree.traverse():

            # Skipping comments
            if node.type == "line_comment" or node.type == "block_comment":
                continue

            node_type = self.get_repr_for_csv_entry(node.type)
            node_val = self.get_repr_for_csv_entry(node.value)

            if node.is_leaf() and node_val and node_type != node_val:
                node_repr = node_type + "," + node_val
            else:
                node_repr = self.get_repr_for_csv_entry(node.type)

            flattened.append(node_repr)
        return flattened

    def get_repr_for_csv_entry(self, entry_repr: Union[str, None]):
        """Return a repr created from the parameter in a way it can be a CSV field."""

        if entry_repr is None:
            entry_repr = ""

        entry_repr = (
            entry_repr.replace(",", ";")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

        return entry_repr


class SimpleMethodFlattener(MethodFlattener):
    def get_before(self) -> List[str]:
        ast = get_sitter_AST(self.before_state.filepath)
        line_pos, col_pos = (
            self.before_state.line + self.line_offset,
            self.before_state.col + self.col_offset,
        )

        method_ast = ast.get_method_by_pos(line_pos, col_pos)
        if not method_ast:
            return []

        return self.get_flatten(method_ast)

    def get_after(self) -> List[str]:
        ast = get_sitter_AST(self.after_state.filepath)
        line_pos, col_pos = (
            self.after_state.line + self.line_offset,
            self.after_state.col + self.col_offset,
        )

        method_ast = ast.get_method_by_pos(line_pos, col_pos)
        if not method_ast:
            return []

        return self.get_flatten(method_ast)


@dataclass
class ChangeMethodFlattener(MethodFlattener):
    before: Union[TreeSitterTree, None] = field(init=False)
    after: Union[TreeSitterTree, None] = field(init=False)
    change_tree: Union[ChangeTree, None] = field(init=False)

    def __post_init__(self):
        self.before = get_sitter_AST(self.before_state.filepath).get_method_by_pos(
            self.before_state.line + self.line_offset,
            self.before_state.col + self.col_offset,
        )
        self.after = get_sitter_AST(self.after_state.filepath).get_method_by_pos(
            self.after_state.line + self.line_offset,
            self.after_state.col + self.col_offset,
        )
        if not self.before or not self.after:
            raise Exception("Before or after states are empty")

        self.change_tree = ChangeTree(self.before, self.after)

    def get_before(self) -> List[str]:
        if not self.change_tree:
            return []

        self.change_tree.create_before()

        return self.get_flatten(self.change_tree)

    def get_after(self) -> List[str]:
        if not self.change_tree:
            return []

        self.change_tree.create_after()
        return self.get_flatten(self.change_tree)


def method_to_csv_line(method: list[str]) -> str:
    return ",".join(method)


def methods_to_csv_lines(
    methods: Union[list[list[str]], Iterable[list[str]]]
) -> Iterator[str]:
    """Convert the methods represented as lists of strings to csv lines."""
    return (method_to_csv_line(method) for method in methods)


def append_methods_to_results(
    methods: Union[list[list[str]], Iterable[list[str]]], filename: Union[Path, str]
) -> None:
    """Append the methds list to the results file."""

    filepath = Path(filename)
    with filepath.open("a", errors="ignore") as fp:
        lines = "\n".join(methods_to_csv_lines(methods))
        fp.write(lines)


def init_results(filename: str, reset=True) -> None:
    """Reset the result CSV, make missing directories."""
    filepath: Path = Path(filename)

    if reset and filepath.exists():
        filepath.unlink()

    filepath.parent.mkdir(parents=True, exist_ok=True)


def get_all_java_files_in_dir(path_to_dir: Union[str, Path]) -> Iterable[Path]:
    """Return a generator providing all files in a directory."""
    path_to_dir = Path(path_to_dir)
    return (
        Path(filepath)
        for filepath in glob.iglob(
            str(path_to_dir.resolve()) + "/**/*.java", recursive=True
        )
        if Path(filepath).is_file()
    )


@click.command()
@click.option(
    "--input",
    "input_",
    type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=True),
    help="Path to the file to be flattened, or to the directory in which all java files will be flattened.",
    required=True,
)
@click.option(
    "--mode", type=click.Choice(["all", "single"], case_sensitive=False), default="all"
)
@click.option("--result", help="The path to the resulting file.", required=True)
@click.option(
    "--method-pos",
    type=str,
    help="Specifies the method's position to flatten, in line:col format. Ignored if mode is not 'single'",
    default="",
)
@click.option(
    "--n-target",
    type=int,
    help="Target number of functions to flatten: at most this many methods will be flattened.",
    default=2_000_000,
)
def main(input_: str, mode: str, result: str, n_target: int, method_pos: str):

    src_path: Path = Path(input_)

    n_methods = 0
    n_files = 0
    logger.info(f"Started flattening.")
    if mode == "all":
        init_results(result)
        logger.info(
            f"Flattening all methods in all java files in directory '{src_path}'. Target number of methods: {n_target}."
        )

        logger.info(f"Flattening done. Files done {n_files}, methods done {n_methods}")

    elif mode == "single":
        if method_pos == "":
            raise Exception("Method must be specified for mode 'single'")

        init_results(result, reset=False)
        # SimpleMethodFlattener(MethodDefinition())
        # flattened_method = flatten_method_in_file(input, method_pos)
        # append_methods_to_results([flattened_method], result)

        logger.info(
            f"Flattening done. Flattening single method in file {src_path} is done."
        )

    else:
        raise Exception("Unkown type - this should never happen")


if __name__ == "__main__":
    main()
