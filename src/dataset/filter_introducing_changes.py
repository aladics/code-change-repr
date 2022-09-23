from pathlib import Path
from typing import Final, Iterator, Union
import click
from tqdm import tqdm

from commit_scores import CommitFileScores, IntroducingCommitScores

N_CSV_ENTRIES: Final[int] = 76001


class CVEScoreParseError(Exception):
    pass


def parse_introducing_section(
        scores_lines: list[str], idx: int, repo: str
) -> tuple[list[IntroducingCommitScores], int]:
    """Parses the introducing commits section in a scores file for a CVE entry."""

    introducing_commits: list[IntroducingCommitScores] = []

    curr_idx = idx + 1
    commit_to_add: Union[IntroducingCommitScores, None] = None
    while curr_idx < len(scores_lines) and " CVE-" not in scores_lines[curr_idx]:
        if scores_lines[curr_idx].startswith("  -"):
            if commit_to_add:
                introducing_commits.append(commit_to_add)
            sha = scores_lines[curr_idx].strip().split()[1]
            commit_to_add = IntroducingCommitScores(repo, sha)

            curr_idx += 1
            while scores_lines[curr_idx].startswith("    -"):
                filename = scores_lines[curr_idx].strip().split()[1][:-1]
                similarity = scores_lines[curr_idx + 1].strip().split()[1]
                contribution = scores_lines[curr_idx + 2].strip().split()[1]
                commit_to_add.files.append(
                    CommitFileScores(filename, float(similarity), float(contribution))
                )
                curr_idx += 3
        else:
            curr_idx += 1

    introducing_commits.append(commit_to_add)
    return introducing_commits, curr_idx


def parse_cve_scores(
        scores_lines: list[str], idx: int
) -> tuple[list[IntroducingCommitScores], Union[int, None]]:
    """
    Parses scores from a CVE from starting from a position.

    :param scores_lines: The list of lines of the scores file
    :param idx: The starting line index of the CVE in the scores files

    :return: A tuple, the first element is a list of introducing commits for the CVE
            the second element is the line index for the next CVE if exists else None
    """

    if " CVE-" not in scores_lines[idx]:
        raise CVEScoreParseError("First line isn't an entry start")

    repo = scores_lines[idx + 2].split()[1]

    introducing_section_idx: int = idx + 3
    while "Introducing commit SHAs" not in scores_lines[introducing_section_idx]:
        introducing_section_idx += 1

    (introducing_commits, introducing_section_end_idx) = parse_introducing_section(
        scores_lines, introducing_section_idx, repo
    )

    if not introducing_section_end_idx < len(scores_lines):
        introducing_section_end_idx = None

    return introducing_commits, introducing_section_end_idx


def parse_scores(scores: str) -> list[IntroducingCommitScores]:
    """Parses every introducing commit with scores from a scores file."""
    with Path(scores).open("r") as f:
        lines = f.readlines()

    introducing_commits: list[IntroducingCommitScores] = []

    commits_to_add, next_cve_idx = parse_cve_scores(lines, 0)
    introducing_commits += commits_to_add
    while next_cve_idx:
        commits_to_add, next_cve_idx = parse_cve_scores(lines, next_cve_idx)
        introducing_commits += commits_to_add

    return introducing_commits


def find_commit_by_stripped_repo(
        stripped_repo_name: str,
        commit_sha: str,
        introducing_commits: list[IntroducingCommitScores],
) -> Union[IntroducingCommitScores, None]:
    """
    Returns the introducing commits scores object that matches the parameters.

    """
    return next(
        (
            commit
            for commit in introducing_commits
            if stripped_repo_name == commit.parsed_repo and commit.sha == commit_sha
        ),
        None,
    )


def filter_method_changes(
        src: str, introducing_commits: list[IntroducingCommitScores]
) -> Iterator[str]:
    """
    Processes a csv file line by line and yields lines only that are changed as part of the introduction.

    :param src: The path to the source file
    :param introducing_commits: The introducing commits list containing (among other things) the filenames that were
    changed in the fix later.
    """

    input_file = Path(src).open()

    # Skin the first line, which is the header
    input_file.readline()
    with tqdm(total=N_CSV_ENTRIES) as pbar:
        while line := input_file.readline():
            csv_fields = line.strip().split(",")
            commit_scores = find_commit_by_stripped_repo(
                stripped_repo_name=csv_fields[0],
                commit_sha=csv_fields[9],
                introducing_commits=introducing_commits,
            )
            if commit_scores and commit_scores.is_file_changed(csv_fields[4]):
                yield line
            pbar.update(1)

    input_file.close()
    pbar.close()


@click.command()
@click.option(
    "--input", "src",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="The input file (generated by the commit parser script) that we filter introducing commits from.",
)
@click.option(
    "--scores",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="The path to the file containing the contribution/relevance scores.",
)
@click.option(
    "--output",
    required=True,
    help="The path to the file where the results will be stored.",
)
def main(src: str, scores: str, output: str) -> None:
    introducing_commis = parse_scores(scores)
    output_path = Path(output)

    if output_path.exists():
        output_path.unlink()

    for method_change_line in filter_method_changes(src, introducing_commis):
        with output_path.open("a") as f:
            f.write(method_change_line)


if __name__ == "__main__":
    main()
