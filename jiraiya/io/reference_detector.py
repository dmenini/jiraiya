from collections.abc import Iterator
from pathlib import Path

from tree_sitter import Node
from tree_sitter_language_pack import SupportedLanguage, get_parser

from jiraiya.domain.data import CodeData, ReferenceData, ReferenceType


class ReferenceDetector:
    def __init__(self, codebase_path: Path, language: SupportedLanguage, files: list[Path]) -> None:
        self.codebase_path = codebase_path
        self.language = language
        self.parser = get_parser(language)
        self.files = files

        self.node_handlers = {
            # Shared or Python-specific
            "class_definition": (self._handle_inheritance, ReferenceType.TYPE_ANNOTATION),
            "call": (self._handle_function_call, ReferenceType.CALL),
            "type": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "type_annotation": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "generic_type": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "attribute": (self._handle_attribute_access, ReferenceType.ATTRIBUTE_ACCESS),
            "decorator": (self._handle_decorator, ReferenceType.DECORATOR),
            "assignment": (self._handle_assignment, ReferenceType.ASSIGNMENT),
            "assignment_expression": (self._handle_assignment, ReferenceType.ASSIGNMENT),
            "augmented_assignment": (self._handle_assignment, ReferenceType.ASSIGNMENT),
            "variable_declaration": (self._handle_variable_declaration, ReferenceType.ASSIGNMENT),
            "variable_declarator": (self._handle_variable_declaration, ReferenceType.ASSIGNMENT),
            # Kotlin-specific
            "class_declaration": (self._handle_inheritance, ReferenceType.TYPE_ANNOTATION),
            "object_declaration": (self._handle_inheritance, ReferenceType.TYPE_ANNOTATION),
            "call_expression": (self._handle_function_call, ReferenceType.CALL),
            "type_reference": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "type_arguments": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "user_type": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "property_declaration": (self._handle_assignment, ReferenceType.ASSIGNMENT),
            "parameter": (self._handle_variable_declaration, ReferenceType.ASSIGNMENT),
            "delegation_specifier": (self._handle_inheritance, ReferenceType.TYPE_ANNOTATION),
            "annotation": (self._handle_decorator, ReferenceType.DECORATOR),
            "annotation_entry": (self._handle_decorator, ReferenceType.DECORATOR),
        }

    def resolve_references(self, data: list[CodeData]) -> dict[str, CodeData]:
        """
        Find all references for each CodeData object across all files in the repo.
        Modifies the CodeData objects in place by populating their references list.
        """
        # Create lookups for efficient searching
        # Key: fully qualified name (module.name), Value: CodeData object
        qualified_name_to_code_data = {f"{d.module}.{d.name}".lstrip("."): d.model_copy() for d in data}

        # Process each file to find references
        for file_path in self.files:
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

    def _extract_imports_context(self, root_node: Node) -> dict[str, str]:
        if self.language == "python":
            return self._extract_python_imports_context(root_node)
        if self.language == "kotlin":
            return self._extract_kotlin_imports_context(root_node)
        raise NotImplementedError

    def _extract_python_imports_context(self, root_node: Node) -> dict[str, str]:
        """
        Extract import context from a file to help resolve simple names to qualified names.
        Supports Python-style import statements with optional aliases.
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
                    if len(parts) >= 2:  # noqa: PLR2004
                        simple_name = parts[-1]
                        qualified_name = ".".join(parts)
                        imports_map[simple_name] = qualified_name

            elif node.type == "import_from_statement":
                # Handle: from module.submodule import ClassName
                import_text = node.text.decode()
                # TODO: Extend to other languages
                # Parse "from X import Y" or "from X import Y as Z"
                if "from " in import_text and " import " in import_text:
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

            for child in node.children:
                walk_imports(child)

        walk_imports(root_node)
        return imports_map

    def _extract_kotlin_imports_context(self, root_node: Node) -> dict[str, str]:
        """
        Extract import context from a file to help resolve simple names to qualified names.
        Supports Kotlin-style import statements with optional aliases.
        Returns a mapping of {simple_name_or_alias: qualified_name}.
        """

        imports_map = {}

        def walk_imports(node: Node) -> None:
            if node.type == "import_header":
                import_text = node.text.decode().strip()
                # Remove the "import" keyword
                if import_text.startswith("import "):
                    import_body = import_text[len("import ") :].strip()

                    # Handle alias: e.g. import foo.bar.Baz as BazAlias
                    if " as " in import_body:
                        qualified_name, alias = map(str.strip, import_body.split(" as ", 1))
                        simple_name = alias
                    else:
                        qualified_name = ".".join(import_body.split(".")[:-1])
                        # Simple name is last segment of qualified name, unless wildcard
                        simple_name = None if qualified_name.endswith(".*") else qualified_name.split(".")[-1]

                    if simple_name:
                        imports_map[simple_name] = qualified_name

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

    def _handle_inheritance(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
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

                    yield code_data

    def _handle_function_call(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """Handle function calls and instantiation like 'ClassName()' or 'obj.method()'"""
        function_node = node.child_by_field_name("function")

        if function_node:
            function_text = function_node.text.decode()

            # Extract the base identifier from qualified calls like 'module.Class()'
            base_identifier = function_text.split(".")[0] if "." in function_text else function_text

            code_data = self._resolve_reference_target(base_identifier, qualified_name_to_code_data, imports_context)

            yield code_data

    def _handle_type_annotation(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """
        Handle type annotations like 'def func(param: MyClass)'
        or `Annotated[MyClass, Depends(get_my_class)]`.
        """
        refs = []
        nodes_to_visit = [node]

        while nodes_to_visit:
            current = nodes_to_visit.pop()
            if current.type == "identifier":
                identifier = current.text.decode()
                refs.append((identifier, current))
            elif current.type == "call":
                if current.children and current.children[0].type == "identifier":
                    identifier = current.children[0].text.decode()
                    refs.append((identifier, current.children[0]))

            # Add children to stack to keep exploring recursively
            nodes_to_visit.extend(current.children)

        # Only take first reference
        for identifier, _ in refs:
            code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
            if code_data:
                yield code_data

    def _handle_attribute_access(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """Handle attribute access like 'ClassName.attribute' or 'obj.method'"""
        attr_text = node.text.decode()

        # Extract the base object/class name
        base_name = attr_text.split(".")[0]

        code_data = self._resolve_reference_target(base_name, qualified_name_to_code_data, imports_context)
        yield code_data

    def _handle_decorator(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """Handle decorators like '@ClassName' or '@module.decorator'"""
        decorator_text = node.text.decode()

        # Extract decorator name (remove @ and handle qualified names)
        decorator_name = decorator_text.lstrip("@").split("(")[0].split(".")[0]

        code_data = self._resolve_reference_target(decorator_name, qualified_name_to_code_data, imports_context)
        yield code_data

    def _handle_assignment(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """Handle assignment expressions like 'var = ClassName' or 'var = ClassName()'"""
        assignment_value = None

        # Find the right-hand side of the assignment
        for child in node.children:
            if child.type in ["=", "assignment_operator"]:
                operator_index = node.children.index(child)
                if operator_index + 1 < len(node.children):
                    assignment_value = node.children[operator_index + 1]
                    break

        if assignment_value:
            if assignment_value.type == "identifier":
                identifier = assignment_value.text.decode()
                code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                yield code_data  # return full assignment node instead of just identifier

            if assignment_value.type == "call":
                if assignment_value.children and assignment_value.children[0].type == "identifier":
                    identifier = assignment_value.children[0].text.decode()
                    code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                    yield code_data  # return full assignment node

                if assignment_value.children and assignment_value.children[0].type == "attribute":
                    yield from self._handle_attribute_access(
                        assignment_value.children[0], qualified_name_to_code_data, imports_context
                    )

    def _handle_variable_declaration(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        """Handle variable declarations with initialization like 'MyClass var = new MyClass()'"""
        for child in node.children:
            if child.type in ["call", "identifier", "attribute"]:
                if child.type == "identifier":
                    identifier = child.text.decode()
                    code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                    yield code_data  # full variable declaration node

                if child.type == "call":
                    if child.children and child.children[0].type == "identifier":
                        identifier = child.children[0].text.decode()
                        code_data = self._resolve_reference_target(
                            identifier, qualified_name_to_code_data, imports_context
                        )
                        yield code_data  # full declaration node

                elif child.type == "attribute":
                    yield from self._handle_attribute_access(child, qualified_name_to_code_data, imports_context)

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
