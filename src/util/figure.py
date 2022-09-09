from pathlib import Path
import subprocess

from flattener import MethodDefinition, ChangeMethodFlattener, SimpleMethodFlattener
from tree_utils import TreeUtils
from tree import get_sitter_AST

import click
from click import BadParameter

GV_FILES_DIR = "gv"
FIGURES_DIR = "figures"


def get_change_method_flattener(before_path: Path, before_pos: str, after_path: Path, after_pos: str) \
        -> ChangeMethodFlattener:
    before_method_def = MethodDefinition("", "", before_path, before_pos)
    after_method_def = MethodDefinition("", "", after_path, after_pos)

    return ChangeMethodFlattener(before_method_def, after_method_def)


def get_simple_method_flattener(before_path: Path, before_pos: str, after_path: Path, after_pos: str) \
        -> SimpleMethodFlattener:
    before_method_def = MethodDefinition("", "", before_path, before_pos)
    after_method_def = MethodDefinition("", "", after_path, after_pos)

    return SimpleMethodFlattener(before_method_def, after_method_def)


def create_changed_before_gv(before_path: Path, before_pos: str, after_path: Path, after_pos: str, result_path: str):
    change_method_flattener = get_change_method_flattener(before_path, before_pos, after_path, after_pos)
    change_method_flattener.change_tree.create_before()
    TreeUtils.dump_gv(change_method_flattener.change_tree, result_path)


def create_changed_after_gv(before_path: Path, before_pos: str, after_path: Path, after_pos: str, result_path: str):
    change_method_flattener = get_change_method_flattener(before_path, before_pos, after_path, after_pos)
    change_method_flattener.change_tree.create_after()
    TreeUtils.dump_gv(change_method_flattener.change_tree, result_path)


def create_simple_ast_gv(path: Path, pos: str, result_path: str):
    pos_split = pos.split(":")
    line = int(pos_split[0])
    column = int(pos_split[1])
    ast = get_sitter_AST(path).get_method_by_pos(line, column)
    TreeUtils.dump_gv(ast, result_path)


def generate_figure(gv_file_path: str, figure_path: str):
    """
    Generates a figure from a graphviz (GV) file.
    """
    subprocess.run(["dot", "-Tpng", gv_file_path, "-o", figure_path])


def create_simple(gv_root_path: Path, src: str, pos: str, figures_root_path: Path, figure_suffix: str = ""):
    src_path = Path(src)
    gv_file_path = gv_root_path / (src_path.stem + ".gv")
    create_simple_ast_gv(src, pos, gv_file_path)

    figure_path = figures_root_path / (src_path.stem + figure_suffix + ".png")
    generate_figure(gv_file_path, figure_path)


def create_changed_before(gv_root_path: Path, src: str, pos: str, src_after: str, pos_after: str, figures_root_path: Path):
    src_path = Path(src)
    gv_file_path = gv_root_path / (src_path.stem + "_changed.gv")
    create_changed_before_gv(src, pos, src_after, pos_after, gv_file_path)

    figure_path = figures_root_path / (src_path.stem + "_changed.png")
    generate_figure(gv_file_path, figure_path)


def create_changed_after(gv_root_path: Path, src: str, pos: str, src_after: str, pos_after: str, figures_root_path: Path):
    src_path = Path(src_after)
    gv_file_path = gv_root_path / (src_path.stem + "_changed.gv")
    create_changed_after_gv(src, pos, src_after, pos_after, gv_file_path)
    figure_path = figures_root_path / (src_path.stem + "_changed.png")
    generate_figure(gv_file_path, figure_path)


@click.command()
@click.option("--src", help="The source java file to generate AST to.",
              type=click.Path(exists=True, readable=True), required=True)
@click.option("--src-after", help="The after state of the source java file.",
              type=click.Path(exists=True, readable=True), default=None)
@click.option("--pos-after", help="The position where the after version of the function is", type=str, default=None)
@click.option("--dst", "dst_root", help="The destination where GraphViz (GV) files and the figures will be stored.",
              type=click.Path(file_okay=False, exists=True), required=True)
@click.option("--pos", help="The position where the function is", type=str, required=True)
@click.option("--type", "ast_type", help="The type of AST to generate",
              type=click.Choice(["simple", "changed-before", "changed-after", "all"], case_sensitive=False),
              default='all', required=True)
def main(src: str, src_after: str, pos_after: str, pos: str, dst_root: str, ast_type: str):
    dst_root_path: Path = Path(dst_root)
    gv_root_path: Path = dst_root_path / GV_FILES_DIR
    figures_root_path: Path = dst_root_path / FIGURES_DIR

    gv_root_path.mkdir(exist_ok=True, parents=True)
    figures_root_path.mkdir(exist_ok=True, parents=True)

    match ast_type:
        case 'simple':
            create_simple(gv_root_path, src, pos, figures_root_path)
        case 'changed-before':
            if src_after is None or pos_after is None:
                raise BadParameter("Using 'changed' AST representation type, an after version of function must also be "
                                   "provided with parameters '--src-after' and '--pos-after'")

            create_changed_before(gv_root_path, src, pos, src_after, pos_after, figures_root_path)
        case 'changed-after':
            if src_after is None or pos_after is None:
                raise BadParameter("Using 'changed' AST representation type, an after version of function must also be "
                                   "provided with parameters '--src-after' and '--pos-after'")

            create_changed_after(gv_root_path, src, pos, src_after, pos_after, figures_root_path)
        case 'all':
            if src_after is None or pos_after is None:
                raise BadParameter("Using 'all' AST representation type, an after version of function must also be "
                                   "provided with parameters '--src-after' and '--pos-after'")

            if not dst_root_path.exists() or not dst_root_path.is_dir():
                raise BadParameter("Using 'all' AST representation type, parameter '--dst' must be an existing "
                                   "directory.")

            create_simple(gv_root_path, src, pos, figures_root_path, "_simple")
            create_simple(gv_root_path, src_after, pos_after, figures_root_path, "_simple")
            create_changed_before(gv_root_path, src, pos, src_after, pos_after, figures_root_path)
            create_changed_after(gv_root_path, src, pos, src_after, pos_after, figures_root_path)


if __name__ == "__main__":
    main()
