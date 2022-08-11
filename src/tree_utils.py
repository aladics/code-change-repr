from __future__ import annotations

from pathlib import Path
from typing import Union
from src.node import Node


class TreeUtils:
    def __init__(self, tree):
        self.tree = tree

    @staticmethod
    def get_gv_repr(tree) -> str:
        """Get a tree's graphviz representation"""
        nodes: list[Node] = [tree.get_root()]

        edges = []
        labels = []

        while nodes:
            node = nodes.pop()
            node_id = node.id

            if node.is_leaf():
                label = node.repr.replace('"', '\\"')
                labels.append(f'{node_id} [label="{label}"]')
                continue

            labels.append(f'{node_id} [label="{node.repr}"]')
            for child in node.children:
                edges.append(f"{node_id} -> {child.id};")
                nodes.append(child)

        lines = ["digraph G{"]
        lines += edges
        lines.append("")
        lines += labels
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def dump_gv(tree, filepath: str) -> None:
        """Dumps a tree's gv representation to a file."""
        gv_repr = TreeUtils.get_gv_repr(tree)
        with Path(filepath).open("w") as f:
            f.write(gv_repr)

    @staticmethod
    def get_node_seq_repr(node_seq: list[Node]) -> list[Union[str, None]]:
        """
        Get the node representation for each node in a sequence.

        :param list[Node] node_seq: The input node sequence.
        """

        return [node.repr for node in node_seq]
