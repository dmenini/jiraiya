from collections.abc import Iterator
from pathlib import Path

from tree_sitter import Node

from jiraiya.domain.data import CodeData, ReferenceType
from jiraiya.indexing.reference_detector_base import ReferenceDetector


class PythonReferenceDetector(ReferenceDetector):
    def __init__(self, codebase_path: Path, files: list[Path]) -> None:
        super().__init__(codebase_path, files)
        self._language = "python"

        self.node_handlers = {
            "class_definition": (self._handle_inheritance, ReferenceType.INHERITANCE),
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
        }

    def _extract_imports_context(self, root_node: Node) -> dict[str, str]:
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
