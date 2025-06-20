import ast
import logging
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from pathspec import PathSpec
from tree_sitter import Node
from tree_sitter_language_pack import SupportedLanguage, get_parser

from doc_scribe.domain.data import ClassData, MethodData, ReferenceData

log = logging.getLogger(__name__)

WHITELIST_FILES = [".java", ".py", ".js", ".rs", ".kt"]

NODE_TYPES = {
    "python": {"class": "class_definition", "method": "function_definition"},
    "java": {"class": "class_declaration", "method": "method_declaration"},
    "rust": {"class": "struct_item", "method": "function_item"},
    "javascript": {"class": "class_declaration", "method": "method_definition"},
    # Add other languages as needed
}

REFERENCE_IDENTIFIERS = {
    "python": {"class": "identifier", "method": "call", "child_field_name": "function"},
    "java": {"class": "identifier", "method": "method_invocation", "child_field_name": "name"},
    "javascript": {"class": "identifier", "method": "call_expression", "child_field_name": "function"},
    "rust": {"class": "identifier", "method": "call_expression", "child_field_name": "function"},
    # Add other languages as needed
}

FILE_EXTENSION_LANGUAGE_MAP: dict[str, SupportedLanguage] = {
    ".java": "java",
    ".py": "python",
    ".js": "javascript",
    ".kt": "kotlin",
}

BLACKLIST = [".venv", "venv", ".git"]


class CodeBaseParser:
    CLASS_NODE_TYPES: ClassVar = {"class_definition", "class_declaration"}
    METHOD_NODE_TYPES: ClassVar = {"function_definition", "method_declaration"}
    CLASS_REF_PARENT_TYPES: ClassVar = {"type", "class_type", "object_creation_expression"}
    METHOD_REF_PARENT_TYPES: ClassVar = {"call_expression", "method_invocation"}

    def __init__(self, codebase_path: Path, *, blacklist: list | None = None, preload: bool = True) -> None:
        self.codebase_path = codebase_path
        self.repo = codebase_path.name
        self.blacklist = (blacklist or []) + BLACKLIST

        if preload:
            self.source_files = self.load_files(codebase_path)
        else:
            self.source_files = []

        self.references = {"class": defaultdict(list), "method": defaultdict(list)}

    def load_files(self, codebase_path: Path) -> list[tuple[Path, SupportedLanguage]]:
        file_list = []
        to_ignore = load_gitignore(codebase_path)

        for path in codebase_path.rglob("*"):
            # Check against .gitignore
            if path.is_file() and self._should_include_file(path, to_ignore):
                language = FILE_EXTENSION_LANGUAGE_MAP.get(path.suffix)
                if language:
                    file_list.append((path, language))
                else:
                    log.info("Unsupported file extension %s in file %s. Skipping.", path.suffix, path)
        return file_list

    def _should_include_file(self, path: Path, spec: PathSpec | None) -> bool:
        rel_path = path.relative_to(self.codebase_path)
        rel_str = str(rel_path)

        # Rule 1: skip if matched by blacklist
        for pattern in self.blacklist:
            if rel_str == pattern or rel_str.startswith(f"{pattern}/"):
                return False

        # Rule 2: always allow whitelisted files
        if path.suffix in WHITELIST_FILES:
            return True

        # Rule 3: skip if ignored by .gitignore
        if spec and spec.match_file(rel_str):  # noqa: SIM103
            return False

        return True

    def extract_ast_nodes(self) -> tuple[list[ClassData], list[MethodData]]:
        class_data: list[ClassData] = []
        method_data: list[MethodData] = []
        files_by_language = self._group_files_by_language(self.source_files)

        for language, files in files_by_language.items():
            parser = get_parser(language)
            for file_path in files:
                code = file_path.read_text(encoding="utf-8")
                tree = parser.parse(code.encode("utf-8"))
                root_node = tree.root_node

                class_nodes, method_nodes = self._extract_class_and_method_nodes(root_node)

                class_data.extend(self._process_class_nodes(class_nodes, file_path, code))
                method_data.extend(self._process_method_nodes(method_nodes, file_path, code))

        return class_data, method_data

    def _group_files_by_language(
        self, file_list: list[tuple[Path, SupportedLanguage]]
    ) -> dict[SupportedLanguage, list[Path]]:
        files_by_language: dict[SupportedLanguage, list[Path]] = defaultdict(list)
        for file_path, language in file_list:
            files_by_language[language].append(file_path)
        return files_by_language

    def _extract_class_and_method_nodes(self, root_node: Node) -> tuple[list[Node], list[Node]]:
        class_nodes: list[Node] = []
        standalone_function_nodes: list[Node] = []

        def walk(node: Node, inside_class: bool = False) -> None:
            if node.type in self.CLASS_NODE_TYPES:
                class_nodes.append(node)
                # When entering a class, set inside_class=True
                for child in node.children:
                    walk(child, inside_class=True)
            elif node.type in self.METHOD_NODE_TYPES:
                if not inside_class:
                    standalone_function_nodes.append(node)
                # Continue walking even from standalone functions
                for child in node.children:
                    walk(child, inside_class)
            else:
                for child in node.children:
                    walk(child, inside_class)

        walk(root_node)
        return class_nodes, standalone_function_nodes

    def _process_class_nodes(self, class_nodes: list[Node], file_path: Path, code: str) -> list[ClassData]:
        processed = []
        for class_node in class_nodes:
            full_source = self._get_full_source_with_annotations(class_node, code)
            processed.append(
                ClassData(
                    repo=self.repo,
                    file_path=file_path.relative_to(self.codebase_path),
                    name=class_node.child_by_field_name("name").text.decode(),
                    source_code=full_source,
                    docstring=self._extract_docstring(class_node, code),
                )
            )
        return processed

    def _process_method_nodes(self, method_nodes: list[Node], file_path: Path, code: str) -> list[MethodData]:
        processed = []
        for method_node in method_nodes:
            name_node = method_node.child_by_field_name("name")
            if name_node:
                method_name = name_node.text.decode()
                full_source = self._get_full_source_with_annotations(method_node, code)
                processed.append(
                    MethodData(
                        repo=self.repo,
                        file_path=file_path.relative_to(self.codebase_path),
                        name=method_name,
                        source_code=full_source,
                        docstring=self._extract_docstring(method_node, code),
                    )
                )
        return processed

    def _extract_docstring(self, node: Node, code: str) -> str:
        # Look into the body block for a string literal
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "expression_statement" and child.children:
                    expr = child.children[0]
                    if expr.type == "string":
                        raw_docstring = code[expr.start_byte : expr.end_byte]
                        return ast.literal_eval(raw_docstring)  # Unescape Python string
        return ""

    def _find_annotations_for_node(self, target_node: Node, code: str) -> list[str]:
        """
        Find decorators/annotations that precede a function or method node.
        Returns a list of annotation strings (e.g., ['@contextmanager', '@lru_cache(maxsize=128)']).
        """
        annotations = []

        # Get the parent node to search for decorators
        parent = target_node.parent
        if not parent:
            return annotations

        # Find the index of our target node in the parent's children
        target_index = None
        for i, child in enumerate(parent.children):
            if child == target_node:
                target_index = i
                break

        if target_index is None:
            return annotations

        # Look backwards from the target node to find decorators
        # Decorators typically appear as 'decorator' nodes in tree-sitter
        for i in range(target_index - 1, -1, -1):
            child = parent.children[i]

            if child.type in ["decorator", "annotation"]:
                decorator_text = code[child.start_byte : child.end_byte].strip()
                annotations.insert(0, decorator_text)  # Insert at beginning to maintain order
            elif child.type not in ["comment", "line_comment", "block_comment"] and child.text.decode().strip():
                break

        return annotations

    def _get_full_source_with_annotations(self, node: Node, code: str) -> str:
        """
        Get the complete source code for a method including its decorators/annotations.
        """
        annotations = self._find_annotations_for_node(node, code)
        source = code[node.start_byte : node.end_byte]

        if annotations:
            # Join annotations with newlines and add the method source
            return "\n".join(annotations) + "\n" + source

        return source

    def resolve_references(
        self, class_data: list[ClassData], method_data: list[MethodData]
    ) -> tuple[list[ClassData], list[MethodData]]:
        """Populate self.references with found references."""
        files_by_language = self._group_files_by_language(self.source_files)
        class_names = {c.name for c in class_data}
        method_names = {m.name for m in method_data}

        for language, files in files_by_language.items():
            parser = get_parser(language)

            for file_path in files:
                code = file_path.read_text(encoding="utf-8")
                code_bytes = code.encode("utf-8")
                root = parser.parse(code_bytes).root_node

                for node, parent in self._traverse_tree_with_parents(root):
                    if node.type != "identifier":
                        continue  # Skip early

                    name = code_bytes[node.start_byte : node.end_byte].decode("utf-8")
                    parent_type = parent.type

                    ref_type = None
                    if name in class_names and parent_type in self.CLASS_REF_PARENT_TYPES:
                        ref_type = "class"
                    elif name in method_names and parent_type in self.METHOD_REF_PARENT_TYPES:
                        ref_type = "name"

                    if ref_type is None:
                        continue

                    reference_text = code_bytes[parent.start_byte : parent.end_byte].decode("utf-8")
                    reference = ReferenceData(
                        file=file_path,
                        line=node.start_point[0] + 1,
                        column=node.start_point[1] + 1,
                        text=reference_text,
                    )
                    self.references[ref_type][name].append(reference)

        class_data = self._map_references_to_classes(class_data)
        method_data = self._map_references_to_methods(method_data)

        return class_data, method_data

    def _traverse_tree_with_parents(self, root: Node) -> Iterator[tuple[Node, Node]]:
        """Yield (node, parent) pairs in depth-first traversal."""
        stack = [(child, root) for child in reversed(root.children)]
        while stack:
            node, parent = stack.pop()
            yield node, parent
            stack.extend((child, node) for child in reversed(node.children))

    def _map_references_to_classes(self, class_data: list[ClassData]) -> list[ClassData]:
        class_data_dict = {cd.name: cd for cd in class_data}
        for class_name, refs in self.references["class"].items():
            if class_name in class_data_dict:
                class_data_dict[class_name].references = refs

        return list(class_data_dict.values())

    def _map_references_to_methods(self, method_data: list[MethodData]) -> list[MethodData]:
        method_data_dict = {(md.parent_name, md.name): md for md in method_data}
        for method_name, refs in self.references["method"].items():
            for key in method_data_dict:
                if key[1] == method_name:
                    method_data_dict[key].references = refs

        return list(method_data_dict.values())


def load_gitignore(codebase_path: Path) -> PathSpec | None:
    gitignore_file = codebase_path / ".gitignore"
    if gitignore_file.exists():
        with gitignore_file.open() as f:
            return PathSpec.from_lines("gitwildmatch", f)
    return None
