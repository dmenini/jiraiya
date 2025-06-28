from abc import ABC, abstractmethod
from pathlib import Path

from tree_sitter import Node
from tree_sitter_language_pack import SupportedLanguage, get_parser

from jiraiya.domain.data import CodeData, ReferenceData


class ReferenceDetector(ABC):
    def __init__(self, codebase_path: Path, files: list[Path]) -> None:
        self.codebase_path = codebase_path
        self.files = files

        self._language: SupportedLanguage | None = None
        self.node_handlers = {}

    @property
    def language(self) -> SupportedLanguage:
        if not self._language:
            raise ValueError
        return self._language

    def resolve_references(self, data: list[CodeData]) -> dict[str, CodeData]:
        """
        Find all references for each CodeData object across all files in the repo.
        Modifies the CodeData objects in place by populating their references list.
        """
        # Create lookups for efficient searching
        # Key: fully qualified name (module.name), Value: CodeData object
        qualified_name_to_code_data = {f"{d.module}.{d.name}".lstrip("."): d.model_copy() for d in data}

        # Process each file to find references
        parser = get_parser(self.language)
        for file_path in self.files:
            code = file_path.read_text()
            tree = parser.parse(code.encode("utf-8"))
            root_node = tree.root_node
            self._find_references_in_file(file_path, code, root_node, qualified_name_to_code_data)

        return qualified_name_to_code_data

    def _find_references_in_file(
        self,
        file_path: Path,
        code: str,
        root_node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
    ) -> None:
        """Find all references in a single file."""

        # First, extract imports to understand the context
        imports_context = self._extract_imports_context(root_node)

        # Add fake imports for locally defined symbols
        for data in qualified_name_to_code_data.values():
            if data.file_path == file_path.relative_to(self.codebase_path):
                imports_context[data.name] = f"{data.module}.{data.name}"

        def walk_node(node: Node) -> None:
            # Check current node for references
            self._check_node_for_references(node, file_path, code, qualified_name_to_code_data, imports_context)

            # Recursively check children
            for child in node.children:
                walk_node(child)

        walk_node(root_node)

    @abstractmethod
    def _extract_imports_context(self, root_node: Node) -> dict[str, str]:
        raise NotImplementedError

    def _check_node_for_references(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Check a specific node for references and add them to the appropriate CodeData objects."""
        handler_tuple = self.node_handlers.get(node.type)
        if not handler_tuple:
            return

        handler_func, ref_type = handler_tuple
        for data in handler_func(node, qualified_name_to_code_data, imports_context):
            if ref_type and data:
                line, column = self._get_line_column(node, code)
                reference = ReferenceData(
                    type=ref_type,
                    file=file_path,
                    line=line,
                    column=column,
                    text=node.text.decode().strip(),
                )
                if self._is_relevant_reference(data, reference):
                    data.references.append(reference)

    def _get_line_column(self, node: Node, code: str) -> tuple[int, int]:
        """Get line and column numbers for a node (1-indexed)"""
        lines_before = code[: node.start_byte].count("\n")
        line_start = code.rfind("\n", 0, node.start_byte) + 1
        column = node.start_byte - line_start
        return lines_before + 1, column + 1

    def _resolve_reference_target(
        self,
        identifier: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> CodeData | None:
        """Resolve an identifier to the appropriate CodeData object."""
        # 1. Try exact qualified match first
        if identifier in qualified_name_to_code_data:
            return qualified_name_to_code_data[identifier]

        # 2. Check if it's imported with a qualified name
        if identifier in imports_context:
            qualified_name = imports_context[identifier]
            if qualified_name in qualified_name_to_code_data:
                return qualified_name_to_code_data[qualified_name]
            return None
        return None

    def _is_relevant_reference(self, data: CodeData, reference: ReferenceData) -> bool:
        """
        Determine if a reference is relevant to a specific CodeData object.
        This helps with disambiguation when multiple objects have the same name.
        """
        # For now, assume all references with matching names are relevant
        # TODO add more sophisticated logic here, such as:
        # - Checking import paths
        # - Analyzing module structure
        # - Using qualified names

        # Avoid multiple references of the same type at the same line
        existing = [
            ref
            for ref in data.references
            if ref.type == reference.type and ref.file == reference.file and ref.line == reference.line
        ]
        return not existing
