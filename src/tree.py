from __future__ import annotations
from typing import Iterator
from pathlib import Path
from itertools import chain

from tree_sitter import Tree, Language, Parser, Node

from node import TreeSitterNode


Language.build_library(
    # Store the library in the `build` directory
    "build/my-languages.so",
    # Include one or more languages
    ["vendor/tree-sitter-java"],
)

JAVA_LANGUAGE = Language("build/my-languages.so", "java")
parser = Parser()
parser.set_language(JAVA_LANGUAGE)


class TreeSitterTree:
    def __init__(self, root_node: Node):
        """Construct tree from it's root node."""
        self.root = root_node

    def traverse(self) -> Iterator[TreeSitterNode]:
        """Do BFS on the tree."""
        cursor = self.root.walk()

        reached_root = False
        while not reached_root:
            yield TreeSitterNode(cursor.node)

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            retracing = True
            while retracing:
                if not cursor.goto_parent():
                    retracing = False
                    reached_root = True

                if cursor.goto_next_sibling():
                    retracing = False

    def get_root(self) -> TreeSitterNode:
        """Get the tree's root node."""
        return TreeSitterNode(self.root.walk().node)

    def get_root_path(self, node: TreeSitterNode) -> list[TreeSitterNode]:
        """Get the root path to the parameter node."""
        root_path = [node]

        while node := node.parent:  # type: ignore
            root_path = [node] + root_path

        return root_path

    def get_root_paths(self) -> list[list[TreeSitterNode]]:
        """Get the root paths for every leaf in the tree."""
        root_paths = []

        for node in self.traverse():
            if node.is_leaf():
                root_paths.append(self.get_root_path(node))

        return root_paths

    def get_subtrees(self, node_type: str) -> Iterator[TreeSitterTree]:
        """Get every subtree for a specific type."""

        for node in self.traverse():
            if node.type == node_type:
                yield TreeSitterTree(node)

    def get_method_by_pos(self, line: int, col: int) -> TreeSitterTree | None:

        for method in chain(
            self.get_subtrees(node_type="method_declaration"),
            self.get_subtrees(node_type="constructor_declaration"),
        ):
            method_root: Node = method.root.node_
            if method_root.start_point[0] <= line <= method_root.end_point[0]:
                return TreeSitterTree(method.root)


def get_AST(filepath: Path | str) -> Tree:
    """Pass in a filepath to get the corresponding AST."""

    filepath = Path(filepath)
    with filepath.open("rb") as fp:
        file_content = fp.read(-1)

    return parser.parse(file_content)


def get_sitter_AST(filepath: Path) -> TreeSitterTree:
    ast = get_AST(filepath)
    return TreeSitterTree(ast.root_node)
