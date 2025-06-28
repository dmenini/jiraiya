from pathlib import Path

import pytest
from tree_sitter_language_pack import get_parser

from jiraiya.domain.data import CodeData, ReferenceType
from jiraiya.indexing.python_reference_detector import PythonReferenceDetector


# Test fixtures and helper functions
@pytest.fixture
def detector() -> PythonReferenceDetector:
    return PythonReferenceDetector(codebase_path=Path("test"), files=[])


@pytest.fixture
def sample_code_data() -> dict[str, CodeData]:
    return {
        "module.ParentClass": CodeData(
            type="class", repo="test", file_path=Path("module/test.py"), name="ParentClass", source_code=""
        ),
        "module.MyClass": CodeData(
            type="class", repo="test", file_path=Path("module/test.py"), name="MyClass", source_code=""
        ),
        "lib.SomeClass": CodeData(
            type="class", repo="test", file_path=Path("lib/test.py"), name="SomeClass", source_code=""
        ),
        "module.MyType": CodeData(
            type="class", repo="test", file_path=Path("module/test.py"), name="MyType", source_code=""
        ),
        "module.my_decorator": CodeData(
            type="function", repo="test", file_path=Path("module/test.py"), name="my_decorator", source_code=""
        ),
        "module.get_my_class": CodeData(
            type="function", repo="test", file_path=Path("module/test.py"), name="get_my_class", source_code=""
        ),
    }


@pytest.fixture
def sample_imports_context() -> dict[str, str]:
    return {
        "ParentClass": "module.ParentClass",
        "MyClass": "module.MyClass",
        "SomeClass": "lib.SomeClass",
        "MyType": "module.MyType",
        "my_decorator": "module.my_decorator",
        "get_my_class": "module.get_my_class",
    }


def test_class_inheritance_single_parent(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of single class inheritance."""

    file_path = Path("test/test_file.py")
    code = """
    class ChildClass(ParentClass):
        pass
    """
    detector._extract_imports_context = lambda _: sample_imports_context

    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    parent_data = sample_code_data["module.ParentClass"]
    assert len(parent_data.references) == 1
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == code.strip()


def test_class_inheritance_multiple_parents(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of multiple inheritance."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    class Child(ParentClass, MixinClass):
        pass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should detect ParentClass reference
    parent_data = sample_code_data["module.ParentClass"]
    assert len(parent_data.references) == 1
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == code.strip()


def test_class_inheritance_same_file(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of multiple inheritance."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
class ParentClass:
    pass

class MyClass(ParentClass):
    pass
"""
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should detect ParentClass reference
    parent_data = sample_code_data["module.ParentClass"]
    assert len(parent_data.references) == 1
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == "class MyClass(ParentClass):\n    pass"


def test_function_call_simple(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple function calls."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    MyClass()
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["module.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == code.strip()


def test_function_call_qualified(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of qualified function calls."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    lib.MyClass()
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should find reference based on base name "lib"
    # Since "lib" is not in our test data, no reference should be added
    for code_data in sample_code_data.values():
        assert len(code_data.references) == 0


def test_type_annotation_simple(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple type annotations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
def func(param: MyType):
    pass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["module.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"


def test_type_annotation_generic(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of generic type annotations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
def func(param: List[MyType]):
    pass
    """

    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["module.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "List[MyType]"


def test_type_annotation_annotated(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of generic type annotations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
def func(param: Annotated[MyType, Depends(get_my_class)]):
    pass
    """

    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["module.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "Annotated[MyType, Depends(get_my_class)]"

    type_data = sample_code_data["module.get_my_class"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "Annotated[MyType, Depends(get_my_class)]"


def test_attribute_access_simple(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of attribute access."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    MyClass.attribute
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["module.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.ATTRIBUTE_ACCESS
    assert class_data.references[0].text == code.strip()


def test_method_access(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple identifier usage."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    MyClass.run()
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["module.MyClass"]
    assert len(class_data.references) == 2  # noqa: PLR2004
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == code.strip()
    assert class_data.references[1].type == ReferenceType.ATTRIBUTE_ACCESS
    assert class_data.references[1].text == "MyClass.run"


def test_decorator_simple(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple decorators."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
@my_decorator
def func():
    pass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    decorator_data = sample_code_data["module.my_decorator"]
    assert len(decorator_data.references) == 1
    assert decorator_data.references[0].type == ReferenceType.DECORATOR
    assert decorator_data.references[0].text == "@my_decorator"


def test_decorator_with_parentheses(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of decorators with parentheses."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
@my_decorator()
def func():
    pass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    decorator_data = sample_code_data["module.my_decorator"]
    assert len(decorator_data.references) == 2  # noqa: PLR2004
    assert decorator_data.references[0].type == ReferenceType.DECORATOR
    assert decorator_data.references[0].text == "@my_decorator()"
    assert decorator_data.references[1].type == ReferenceType.CALL
    assert decorator_data.references[1].text == "my_decorator()"


def test_assignment_identifier(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of assignment to identifier."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    var = MyClass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    assigned_data = sample_code_data["module.MyClass"]
    assert len(assigned_data.references) == 1
    assert assigned_data.references[0].type == ReferenceType.ASSIGNMENT
    assert assigned_data.references[0].text == code.strip()


def test_assignment_call(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of assignment to function call."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    var = MyClass()
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    some_data = sample_code_data["module.MyClass"]
    assert len(some_data.references) == 2  # noqa: PLR2004
    assert some_data.references[0].type == ReferenceType.ASSIGNMENT
    assert some_data.references[0].text == code.strip()
    assert some_data.references[1].type == ReferenceType.CALL
    assert some_data.references[1].text == "MyClass()"


def test_no_reference_when_not_found(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test that no reference is created when identifier is not found."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    UnknownClass
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # No references should be added to any CodeData objects
    for code_data in sample_code_data.values():
        assert len(code_data.references) == 0


def test_unsupported_node_type(
    detector: PythonReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test handling of unsupported node types."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.py")
    code = """
    # This is a comment that will create an unsupported node type
    """
    node = get_parser("python").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # No references should be added
    for code_data in sample_code_data.values():
        assert len(code_data.references) == 0
