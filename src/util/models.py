from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from code_changes.cache import Cache


@dataclass
class MethodDefinition:
    repo: str
    sha: str
    filepath: Path
    pos: str
    line: int = field(init=False)
    col: int = field(init=False)

    def __post_init__(self):
        positions = self.pos.split(":")
        self.line = int(positions[0])
        self.col = int(positions[1])

    @classmethod
    def before_method_from_csv_line(cls: MethodDefinition, line: str):
        csv_fields = line.split(",")
        return cls(csv_fields[0], csv_fields[8], csv_fields[3], csv_fields[5])

    @classmethod
    def after_method_from_csv_line(cls: MethodDefinition, line: str):
        csv_fields = line.split(",")
        return cls(csv_fields[0], csv_fields[9], csv_fields[3], csv_fields[5])


@dataclass
class ChangedMethodEntry:
    """
    Corresponds to an entry in a code change entry in a file of code changes (CSV)

    """

    label: int
    before_state: MethodDefinition
    after_state: MethodDefinition

    @classmethod
    def from_csv_line(cls: ChangedMethodEntry, line: str, cache: Cache):
        csv_fields = line.split(",")
        before_path = cache.get_or_download(rel_path=Cache.get_rel_path(csv_fields[0], csv_fields[8], csv_fields[3]),
                                            url=csv_fields[1], is_before=True)
        after_path = cache.get_or_download(rel_path=Cache.get_rel_path(csv_fields[0], csv_fields[9], csv_fields[4]),
                                           url=csv_fields[2], is_before=False)
        before_state = MethodDefinition(csv_fields[0], csv_fields[8], before_path, csv_fields[5])
        after_state = MethodDefinition(csv_fields[0], csv_fields[9], after_path, csv_fields[6])
        return cls(int(csv_fields[10].strip()), before_state, after_state)
