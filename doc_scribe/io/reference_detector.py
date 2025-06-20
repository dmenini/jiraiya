from pathlib import Path

from tree_sitter import Node
from tree_sitter_language_pack import SupportedLanguage, get_parser

from doc_scribe.domain.data import CodeData, ReferenceData, ReferenceType


class ReferenceDetector:
    def __init__(self, codebase_path: Path, language: SupportedLanguage):
        self.codebase_path = codebase_path
        self.parser = get_parser(language)

    def resolve_references(self, data: list[CodeData], all_files: list[Path]) -> dict[str, CodeData]:
        """
        Find all references for each CodeData object across all files in the repo.
        Modifies the CodeData objects in place by populating their references list.
        """
        # Create lookups for efficient searching
        # Key: fully qualified name (module.name), Value: CodeData object
        qualified_name_to_code_data = {}

        for code_data in data:
            # Fully qualified name
            qualified_name = f"{code_data.module}.{code_data.name}".lstrip(".")
            qualified_name_to_code_data[qualified_name] = code_data

        # Process each file to find references
        for file_path in all_files:
            code = file_path.read_text()
            tree = self.parser.parse(code.encode("utf-8"))
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

        def walk_node(node: Node) -> None:
            # Check current node for references
            self._check_node_for_references(node, file_path, code, qualified_name_to_code_data, imports_context)

            # Recursively check children
            for child in node.children:
                walk_node(child)

        walk_node(root_node)

    def _extract_imports_context(self, root_node: Node) -> dict[str, str]:
        """
        Extract import context from a file to help resolve simple names to qualified names.
        Returns a mapping of {simple_name: qualified_name} based on imports.
        """
        imports_map = {}

        def walk_imports(node: Node) -> None:
            if node.type == "import_statement":
                # Handle: import module.submodule.ClassName
                import_text = node.text.decode()
                if "." in import_text:
                    # Extract the qualified name and simple name
                    parts = import_text.replace("import", "").strip().split(".")
                    if len(parts) >= 2:
                        simple_name = parts[-1]
                        qualified_name = ".".join(parts)
                        imports_map[simple_name] = qualified_name

            elif node.type == "import_from_statement":
                # Handle: from module.submodule import ClassName
                import_text = node.text.decode()
                try:
                    # Parse "from X import Y" or "from X import Y as Z"
                    if "from" in import_text and "import" in import_text:
                        from_part = import_text.split(" import ")[0].replace("from ", "").strip()
                        import_part = import_text.split(" import ")[1].strip()

                        # Handle multiple imports or aliases
                        imported_items = [item.strip() for item in import_part.split(",")]
                        for item in imported_items:
                            if " as " in item:
                                original_name, alias = item.split(" as ")
                                imports_map[alias.strip()] = f"{from_part}.{original_name.strip()}"
                            else:
                                imports_map[item] = f"{from_part}.{item}"
                except:
                    pass  # Skip malformed imports

            for child in node.children:
                walk_imports(child)

        walk_imports(root_node)
        return imports_map

    def _check_node_for_references(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Check a specific node for references and add them to the appropriate CodeData objects."""
        # Class inheritance
        if node.type in ["class_definition", "class_declaration"]:
            self._handle_inheritance(node, file_path, code, qualified_name_to_code_data, imports_context)

        # Function calls and instantiation
        elif node.type == "call":
            self._handle_function_call(node, file_path, code, qualified_name_to_code_data, imports_context)

        # Type annotations
        elif node.type in ["type", "type_annotation", "generic_type"]:
            self._handle_type_annotation(node, file_path, code, qualified_name_to_code_data, imports_context)

        # Attribute access
        elif node.type == "attribute":
            self._handle_attribute_access(node, file_path, code, qualified_name_to_code_data, imports_context)

        # Decorators
        elif node.type == "decorator":
            self._handle_decorator(node, file_path, code, qualified_name_to_code_data, imports_context)

        # General identifier usage
        elif node.type == "identifier":
            self._handle_identifier_usage(node, file_path, code, qualified_name_to_code_data, imports_context)

    def _resolve_reference_target(
        self,
        identifier: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> CodeData | None:
        """
        Resolve an identifier to the appropriate CodeData object(s).
        Returns a list because there might be ambiguity.
        """

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

    def _handle_inheritance(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle class inheritance like 'class Child(Parent)'"""
        # Look for superclass list or extends clause
        superclass_node = node.child_by_field_name("superclasses") or node.child_by_field_name("extends")

        if superclass_node:
            superclass_text = superclass_node.text.decode()

            # Extract individual parent class names
            parent_names = [name.strip() for name in superclass_text.replace("(", "").replace(")", "").split(",")]

            for parent_name in parent_names:
                if parent_name:
                    code_data = self._resolve_reference_target(
                        parent_name, qualified_name_to_code_data, imports_context
                    )

                    if code_data and self._is_relevant_reference(code_data, file_path):
                        line, column = self._get_line_column(superclass_node, code)
                        reference = ReferenceData(
                            type=ReferenceType.INHERITANCE,
                            file=file_path,
                            line=line,
                            column=column,
                            text=superclass_text.strip(),
                        )
                        code_data.references.append(reference)

    def _handle_function_call(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle function calls and instantiation like 'ClassName()' or 'obj.method()'"""
        function_node = node.child_by_field_name("function")
        if not function_node:
            return

        call_text = node.text.decode()
        function_text = function_node.text.decode()

        # Extract the base identifier from qualified calls like 'module.Class()'
        base_identifier = function_text.split(".")[0] if "." in function_text else function_text

        code_data = self._resolve_reference_target(base_identifier, qualified_name_to_code_data, imports_context)

        if code_data and self._is_relevant_reference(code_data, file_path):
            # Determine if it's instantiation or method call
            ref_type = ReferenceType.INSTANTIATION if base_identifier == code_data.name else ReferenceType.METHOD_CALL

            line, column = self._get_line_column(node, code)
            reference = ReferenceData(
                type=ref_type,
                file=file_path,
                line=line,
                column=column,
                text=call_text.strip(),
            )
            code_data.references.append(reference)

    def _handle_type_annotation(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle type annotations like 'def func(param: ClassName)'"""
        type_text = node.text.decode()

        # Extract base type name (handle generics like list[ClassName])
        base_type = type_text.split("[")[0].split(".")[0] if "[" in type_text or "." in type_text else type_text

        code_data = self._resolve_reference_target(base_type, qualified_name_to_code_data, imports_context)

        if code_data and self._is_relevant_reference(code_data, file_path):
            line, column = self._get_line_column(node, code)
            reference = ReferenceData(
                type=ReferenceType.TYPE_ANNOTATION,
                file=file_path,
                line=line,
                column=column,
                text=type_text.strip(),
            )
            code_data.references.append(reference)

    def _handle_attribute_access(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle attribute access like 'ClassName.attribute' or 'obj.method'"""
        attr_text = node.text.decode()

        # Extract the base object/class name
        base_name = attr_text.split(".")[0]

        code_data = self._resolve_reference_target(base_name, qualified_name_to_code_data, imports_context)

        if code_data and self._is_relevant_reference(code_data, file_path):
            line, column = self._get_line_column(node, code)
            reference = ReferenceData(
                type=ReferenceType.ATTRIBUTE_ACCESS,
                file=file_path,
                line=line,
                column=column,
                text=attr_text.strip(),
            )
            code_data.references.append(reference)

    def _handle_decorator(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle decorators like '@ClassName' or '@module.decorator'"""
        decorator_text = node.text.decode()

        # Extract decorator name (remove @ and handle qualified names)
        decorator_name = decorator_text.lstrip("@").split("(")[0].split(".")[0]

        code_data = self._resolve_reference_target(decorator_name, qualified_name_to_code_data, imports_context)

        if code_data and self._is_relevant_reference(code_data, file_path):
            line, column = self._get_line_column(node, code)
            reference = ReferenceData(
                type=ReferenceType.DECORATOR,
                file=file_path,
                line=line,
                column=column,
                text=decorator_text.strip(),
            )
            code_data.references.append(reference)

    def _handle_identifier_usage(
        self,
        node: Node,
        file_path: Path,
        code: str,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> None:
        """Handle general identifier usage"""
        identifier = node.text.decode()

        # Skip if this is the definition itself
        if self._is_definition_node(node):
            return

        # Resolve the identifier to target CodeData objects
        code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)

        if code_data and self._is_relevant_reference(code_data, file_path):
            line, column = self._get_line_column(node, code)
            reference = ReferenceData(
                type=ReferenceType.USAGE,
                file=file_path,
                line=line,
                column=column,
                text=identifier,
            )
            code_data.references.append(reference)

    def _get_line_column(self, node: Node, code: str) -> tuple[int, int]:
        """Get line and column numbers for a node (1-indexed)"""
        lines_before = code[: node.start_byte].count("\n")
        line_start = code.rfind("\n", 0, node.start_byte) + 1
        column = node.start_byte - line_start
        return lines_before + 1, column + 1

    def _is_definition_node(self, node: Node) -> bool:
        """Check if this node is part of a definition (to avoid self-references)"""
        parent = node.parent
        while parent:
            if parent.type in ["class_definition", "function_definition", "method_definition"]:
                # Check if this identifier is the name being defined
                name_node = parent.child_by_field_name("name")
                if name_node and name_node == node:
                    return True
            parent = parent.parent
        return False

    def _is_relevant_reference(self, code_data: CodeData, ref_file_path: Path) -> bool:
        """
        Determine if a reference is relevant to a specific CodeData object.
        This helps with disambiguation when multiple objects have the same name.
        """
        # Don't reference itself
        if code_data.file_path == ref_file_path.relative_to(self.codebase_path):
            return False

        # For now, assume all references with matching names are relevant
        # You could add more sophisticated logic here, such as:
        # - Checking import paths
        # - Analyzing module structure
        # - Using qualified names

        return True
