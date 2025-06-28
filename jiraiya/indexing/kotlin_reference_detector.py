from collections.abc import Iterator
from pathlib import Path

from tree_sitter import Node

from jiraiya.domain.data import CodeData, ReferenceType
from jiraiya.indexing.reference_detector_base import ReferenceDetector


class KotlinReferenceDetector(ReferenceDetector):
    def __init__(self, codebase_path: Path, files: list[Path]) -> None:
        super().__init__(codebase_path, files)
        self._language = "kotlin"

        self.node_handlers = {
            "class_declaration": (self._handle_inheritance, ReferenceType.INHERITANCE),
            "call_expression": (self._handle_function_call, ReferenceType.CALL),
            "type_identifier": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "user_type": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "type_reference": (self._handle_type_annotation, ReferenceType.TYPE_ANNOTATION),
            "property_declaration": (self._handle_variable_declaration, ReferenceType.ASSIGNMENT),
            "binary_expression": (self._handle_assignment, ReferenceType.ASSIGNMENT),
            "navigation_expression": (self._handle_attribute_access, ReferenceType.ATTRIBUTE_ACCESS),
            "annotation": (self._handle_decorator, ReferenceType.DECORATOR),
        }

    def _extract_imports_context(self, root_node: Node) -> dict[str, str]:
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
                        qualified_name = import_body
                        # Handle wildcard imports
                        if qualified_name.endswith(".*"):
                            # For wildcard imports, we can't resolve simple names
                            # but we could store the package for later resolution
                            pass
                        else:
                            # Simple name is the last segment of qualified name
                            simple_name = qualified_name.split(".")[-1]
                            imports_map[simple_name] = qualified_name

            for child in node.children:
                walk_imports(child)

        walk_imports(root_node)
        return imports_map

    def _handle_inheritance(
        self, node: Node, qualified_name_to_code_data: dict[str, CodeData], imports_context: dict[str, str]
    ) -> Iterator[CodeData]:
        # In Kotlin: class Foo : Bar()
        for child in node.children:
            for spec in child.children:
                if spec.type in ("constructor_invocation", "type_identifier", "user_type"):
                    # Handle different inheritance patterns
                    if spec.type == "constructor_invocation":
                        name = spec.text.decode().rstrip("()")
                        code_data = self._resolve_reference_target(name, qualified_name_to_code_data, imports_context)
                        if code_data:
                            yield code_data
                    elif spec.type in ("type_identifier", "user_type"):
                        name = spec.text.decode()
                        code_data = self._resolve_reference_target(name, qualified_name_to_code_data, imports_context)
                        if code_data:
                            yield code_data

    def _handle_function_call(
        self, node: Node, qualified_name_to_code_data: dict[str, CodeData], imports_context: dict[str, str]
    ) -> Iterator[CodeData]:
        # Handle different call patterns
        if node.type == "call_expression":
            # Get the function being called
            for child in node.children:
                if child.type in ("simple_identifier", "navigation_expression"):
                    name = child.text.decode()
                    code_data = self._resolve_reference_target(name, qualified_name_to_code_data, imports_context)
                    if code_data:
                        yield code_data

    def _handle_type_annotation(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        parent_type = node.parent.type if node.parent else None
        # user_type makes TYPE_ANNOTATION a bit too eager, but removing it makes it miss when needed
        if parent_type in ("value_parameter", "variable_declaration", "type_reference", "user_type"):
            if node.type == "type_identifier":
                identifier = node.text.decode()
                code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                if code_data:
                    yield code_data
            elif node.type == "user_type":
                # Handle user-defined types
                type_identifiers = [child for child in node.children if child.type == "type_identifier"]
                if type_identifiers:
                    # Take the first type identifier for the main type
                    identifier = type_identifiers[0].text.decode()
                    code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                    if code_data:
                        yield code_data

    def _handle_attribute_access(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        # Handle navigation expressions like obj.property
        if node.type == "navigation_expression":
            # Get the left side of the navigation
            left_node = node.children[0] if node.children else None
            if left_node and left_node.type == "simple_identifier":
                base_name = left_node.text.decode()
                code_data = self._resolve_reference_target(base_name, qualified_name_to_code_data, imports_context)
                if code_data:
                    yield code_data

    def _handle_decorator(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        # Kotlin annotation: @MyAnnotation
        if node.type == "annotation":
            # Find the annotation name
            for child in node.children:
                if child.type in ("user_type", "simple_identifier"):
                    name = child.text.decode()
                    code_data = self._resolve_reference_target(name, qualified_name_to_code_data, imports_context)
                    if code_data:
                        yield code_data
                else:
                    for spec in child.children:
                        if spec.type in ("user_type", "simple_identifier", "constructor_invocation"):
                            name = spec.text.decode()
                            code_data = self._resolve_reference_target(
                                name, qualified_name_to_code_data, imports_context
                            )
                            if code_data:
                                yield code_data

    def _handle_assignment(
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        # Handle assignment expressions
        if node.type == "assignment":
            # Get the right-hand side of the assignment
            rhs = node.child_by_field_name("right")
            if rhs:
                if rhs.type == "call_expression":
                    yield from self._handle_function_call(rhs, qualified_name_to_code_data, imports_context)
                elif rhs.type in ("simple_identifier", "navigation_expression"):
                    base_name = rhs.text.decode().split(".")[0]
                    code_data = self._resolve_reference_target(base_name, qualified_name_to_code_data, imports_context)
                    if code_data:
                        yield code_data

    def _handle_variable_declaration(  # noqa: C901
        self,
        node: Node,
        qualified_name_to_code_data: dict[str, CodeData],
        imports_context: dict[str, str],
    ) -> Iterator[CodeData]:
        # Handle property declarations: val foo: MyType = ...
        if node.type != "property_declaration":
            return

        # Handle type annotation
        type_node = node.child_by_field_name("type")
        if type_node:
            type_identifiers = []
            if type_node.type == "user_type":
                type_identifiers = [child for child in type_node.children if child.type == "type_identifier"]
            elif type_node.type == "type_identifier":
                type_identifiers = [type_node]

            for identifier_node in type_identifiers:
                identifier = identifier_node.text.decode()
                code_data = self._resolve_reference_target(identifier, qualified_name_to_code_data, imports_context)
                if code_data:
                    yield code_data

        # Handle initializer
        initializer = node.child_by_field_name("initializer")
        if initializer:
            if initializer.type == "call_expression":
                yield from self._handle_function_call(initializer, qualified_name_to_code_data, imports_context)
            elif initializer.type in ("simple_identifier", "navigation_expression"):
                base_name = initializer.text.decode().split(".")[0]
                code_data = self._resolve_reference_target(base_name, qualified_name_to_code_data, imports_context)
                if code_data:
                    yield code_data
