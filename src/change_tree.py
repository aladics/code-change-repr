# from __future__ import annotations
from typing import Iterator, List, Union

from node import ChangeTreeNode, NodeFactory, TreeSitterNode
from tree import TreeSitterTree


class ChangeTree:
    """
    Provides various methods to work with before and after states of codes.
    """

    def __init__(
        self,
        before_tree: TreeSitterTree,
        after_tree: TreeSitterTree,
        max_root_paths: int = 1000,
    ):
        """
        :param before_tree: The tree corresponding to the state of the code before the change.
        :param after_tree: The tree corresponding to the state of the code after the change.
        """

        self.before_tree = before_tree
        self.after_tree = after_tree
        self.root = None
        self.max_root_paths = max_root_paths

        self.before_paths = [
            self.RootPath(path) for path in self.before_tree.get_root_paths()[:self.max_root_paths]
        ]
        self.after_paths = [
            self.RootPath(path) for path in self.after_tree.get_root_paths()[:self.max_root_paths]
        ]

    class RootPath:
        def __init__(self, path: List[TreeSitterNode]):
            self.path = path
            self.node_ids = [node.id for node in path]

        def __hash__(self):
            return hash((*self.node_ids,))

        def __eq__(self, other):
            if len(self.node_ids) != len(other.node_ids):
                return False

            for i in range(len(self.node_ids)):
                if self.node_ids[i] != other.node_ids[i]:
                    return False

            return True

        def __repr__(self) -> str:
            path_repr = f"{self.path[0].repr} -> {self.path[1].repr} -> ... -> {self.path[-2].repr} -> {self.path[-1].repr}"

            return path_repr

    def get_root(self):
        return self.root

    @staticmethod
    def is_aleady_visited(node: ChangeTreeNode, visited_nodes: List[ChangeTreeNode]):
        return any(node.id == visited_node.id for visited_node in visited_nodes)

    def traverse(self) -> Iterator[ChangeTreeNode]:
        """
        Do BFS on the tree.
        """

        visited_nodes: list[ChangeTreeNode] = []
        node: Union[ChangeTreeNode, None] = self.root

        while node:
            if not ChangeTree.is_aleady_visited(node, visited_nodes):
                yield node
                visited_nodes.append(node)

            traverse_up = True
            for child in node.children:
                if not ChangeTree.is_aleady_visited(child, visited_nodes):
                    node = child
                    traverse_up = False
                    break

            if traverse_up:
                node = node.parent

    def create_path_diffs(
        self, base_set: List[RootPath], other_set: List[RootPath]
    ) -> None:
        """
        Create the tree by path diffs.

        :param list[Node] base_set: The set whose unqiue paths we are interested in
        :param list[Node] other_set: The set whose contents we are removing from base_set
        """

        self.root = None

        changed_paths = set()
        changed_paths.update(base_set)
        changed_paths.difference_update(other_set)
        changed_paths = sorted(changed_paths, key=lambda el: base_set.index(el))

        for changed_path in changed_paths:
            self.add_root_path(changed_path.path)

    def create_before(self) -> None:
        """Creates the change tree relative to the before state of the code change."""
        self.create_path_diffs(self.before_paths, self.after_paths)

    def create_after(self) -> None:
        """Creates the change tree relative to the after state of the code change."""
        self.create_path_diffs(self.after_paths, self.before_paths)

    def add_root_path(self, root_path: List[TreeSitterNode]) -> None:
        """
        Add a root path to construct the change tree.
        """

        root_in_path: ChangeTreeNode = NodeFactory.chtree_node_from_sitter_node(
            root_path[0]
        )

        if self.root == None:
            # self.root = NodeFactory.from_tree_sitter_node(root_path[0])
            self.root = root_in_path
        elif not self.root.is_repr_same(root_in_path):
            raise ValueError(
                "Root is inconsistent: it must be the same for all root-paths"
            )

        parent = self.root
        for node_in_path in root_path[1:]:

            next_node = None
            for node_in_tree in parent.children:
                if node_in_tree.is_repr_same(node_in_path):
                    next_node = node_in_tree
                    break

            if next_node:
                parent = next_node
            else:
                new_node: ChangeTreeNode = NodeFactory.chtree_node_from_sitter_node(
                    node_in_path
                )

                new_node.parent = parent
                parent.children.append(new_node)
                parent = new_node
