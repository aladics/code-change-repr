from dataclasses import dataclass, field
from pathlib import Path


class UnknownRepositoryTypeException(Exception):
    pass


@dataclass
class CommitFileScores:
    filename: str
    similarity: float
    contribution: float


@dataclass
class IntroducingCommitScores:
    repo: str
    sha: str = None
    files: list[CommitFileScores] = field(default_factory=list)

    @property
    def parsed_repo(self) -> str:
        repo_str = ""
        parsed_repo_str = self.repo.replace(".git", "")

        if "https://github.com/" in parsed_repo_str:
            repo_str = parsed_repo_str.replace("https://github.com/", "")
        elif (
            "git-wip-us.apache.org" in parsed_repo_str
            or "git.apache.org" in parsed_repo_str
        ):
            repo_str = "apache"
            repo_str += "/" + Path(parsed_repo_str).stem
        else:
            raise UnknownRepositoryTypeException(
                f"Unknown repository type {parsed_repo_str}"
            )

        return repo_str

    def is_file_changed(self, file_path: str) -> bool:
        filename = Path(file_path).name
        return any(filename == file.filename for file in self.files)
