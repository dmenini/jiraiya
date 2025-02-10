import ast
from pathlib import Path
import astpretty


class CodebaseLoader:
    def __init__(self, root_path: Path, exclude: list[str], include: list[str]):
        self.root_path = root_path
        self.exclude = exclude
        self.include = include

    def _get_all_files(self) -> list[Path]:
        """Recursively finds all Python files in the given directory."""
        if self.root_path.is_file() and self.root_path.suffix in ["py", "kt"]:
            return [self.root_path]

        all_files = list(self.root_path.rglob("*.py"))
        return all_files

    def load_file(self, file_path: Path) -> str:
        with file_path.open("r", encoding="utf-8") as f:
            code = f.read()
        return code

    def parse_file(self, file_path: Path) -> str:
        """Parses a Python file and returns its AST."""
        code = self.load_file(file_path)
        tree = ast.parse(code)
        return astpretty.pformat(tree)

    def load_all_files(self) -> dict[str, str]:
        python_files = self._get_all_files()

        tree = {}
        for file in python_files:
            relative_path = file.relative_to(self.root_path)  # Preserve structure
            if self._is_included(relative_path) and not self._is_excluded(relative_path):
                code = self.load_file(file)
                if code:
                    tree[str(relative_path)] = code
        return tree

    def generate_ast_for_codebase(self) -> dict[str, str]:
        """Generates AST for all Python files in the codebase, preserving directory structure."""
        python_files = self._get_all_files()

        ast_trees = {}
        for file in python_files:
            relative_path = file.relative_to(self.root_path)  # Preserve structure
            if self._is_included(relative_path) and not self._is_excluded(relative_path):
                ast_tree = self.parse_file(file)
                if ast_tree:
                    ast_trees[str(relative_path)] = ast_tree

        return ast_trees

    def _is_included(self, file: Path) -> bool:
        if not self.include:
            return True
        return any(str(file).startswith(inc) for inc in self.include)

    def _is_excluded(self, file: Path) -> bool:
        return any(str(file).startswith(exc) for exc in self.exclude)
