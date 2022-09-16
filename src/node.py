from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

# from tree_sitter import Node as TreeSitterNode
import hashlib


@dataclass
class Node(ABC):
    type: str

    @property
    @abstractmethod
    def parent(self) -> Node | None:
        pass

    @property
    @abstractmethod
    def children(self) -> list[Node]:
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def value(self) -> str | None:
        pass

    @property
    @abstractmethod
    def child_rank(self) -> int:
        pass

    @property
    def ancestors(self) -> list[Node]:
        parents = []

        parent = self.parent
        while parent:
            parents.append(parent)
            parent = parent.parent

        return parents

    @property
    def to_node_path(self) -> str:
        concated_ids = ""

        for ancestor in self.ancestors:
            concated_ids += ancestor.relative_id

        return concated_ids

    @property
    def ast_identifier(self) -> str | None:
        """Get the node's identifier, if it has one"""
        if self.is_leaf():
            return self.value
        return None

    @property
    def relative_id(self) -> str:
        """
        Get id for node that is unique as part of a path.
        """
        str_repr = f"{len(self.ancestors)}_{self.child_rank}_{self.type}"

        ast_id = self.ast_identifier
        if ast_id:
            str_repr = f"{str_repr}_{ast_id}"

        # have to hash cause of possible illegal characters
        return f"node_{hashlib.md5(str_repr.encode()).hexdigest()}"

    @property
    def repr(self) -> str:
        """
        Get human readable, non-unique node representation.

        :param Node node: The node to represent.
        """

        node_repr: str = self.type
        if self.is_leaf() and self.value and self.type != self.value:
            node_repr += ": " + self.value

        return node_repr

    def is_repr_same(self, other: Node) -> bool:
        return self.id == other.id

    def is_leaf(self) -> bool:
        return len(self.children) == 0


class TreeSitterNode(Node):
    def __init__(self, node):
        super().__init__(node.type)
        self.node_ = node

    @property
    def id(self) -> str:
        """
        Generate an id for a node that's unique to the node.

        Parameter 'node' must have properties 'type', 'parent', and 'children'

        """

        str_repr = f"{self.relative_id}_{self.to_node_path}"

        # have to hash cause of possible illegal characters
        return f"node_{hashlib.md5(str_repr.encode()).hexdigest()}"

    @property
    def parent(self) -> TreeSitterNode | None:
        if self.node_.parent:
            return TreeSitterNode(self.node_.parent)
        return None

    @property
    def children(self) -> list[TreeSitterNode]:
        return [TreeSitterNode(child) for child in self.node_.children]

    @property
    def value(self) -> str | None:
        return self.node_.text.decode(encoding="utf-8", errors="ignore")

    @property
    def child_rank(self) -> int:
        rank = 0
        if self.parent:
            for sibling in self.parent.children:
                if sibling.node_ == self.node_:
                    break
                elif sibling.type == self.type:
                    rank += 1

        return rank

    def walk(self):
        return self.node_.walk()


class ChangeTreeNode(Node):
    def __init__(
        self,
        id: str,
        child_rank: int,
        type: str,
        value: str | None = None,
        parent: ChangeTreeNode | None = None,
        children: list[ChangeTreeNode] | None = None,
    ):
        super().__init__(type)
        self.id_ = id
        self.child_rank_ = child_rank
        self.value_ = value
        self.parent_ = parent
        if value:
            self.text = value.encode("utf-8")

        if not children:
            self.children_ = []
        else:
            self.children_ = children

    @property
    def id(self) -> str:
        """
        Generate an id for a node that's unique to the node.

        Parameter 'node' must have properties 'type', 'parent', and 'children'

        """

        return self.id_

    @property
    def parent(self) -> ChangeTreeNode | None:
        return self.parent_

    @parent.setter
    def parent(self, new_parent: ChangeTreeNode) -> None:
        self.parent_ = new_parent

    @property
    def children(self) -> list[ChangeTreeNode]:
        return self.children_

    @property
    def value(self) -> str | None:
        return self.value_

    @property
    def child_rank(self) -> int:
        return self.child_rank_


class NodeFactory:
    @staticmethod
    def chtree_node_from_sitter_node(node: TreeSitterNode) -> ChangeTreeNode:
        """Construct ChangeTreeNode from TreeSitterNode object."""
        return ChangeTreeNode(
            node.id,
            node.child_rank,
            node.type,
            node.value,
        )
