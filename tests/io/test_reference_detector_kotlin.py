from pathlib import Path

import pytest
from tree_sitter_language_pack import get_parser

from jiraiya.domain.data import CodeData, ReferenceType
from jiraiya.indexing.kotlin_reference_detector import KotlinReferenceDetector


# Test fixtures and helper functions
@pytest.fixture
def detector() -> KotlinReferenceDetector:
    return KotlinReferenceDetector(codebase_path=Path("test"), files=[])


@pytest.fixture
def sample_code_data() -> dict[str, CodeData]:
    return {
        "com.example.ParentClass": CodeData(
            type="class", repo="test", file_path=Path("com/example/test.kt"), name="ParentClass", source_code=""
        ),
        "com.example.MyClass": CodeData(
            type="class", repo="test", file_path=Path("com/example/test.kt"), name="MyClass", source_code=""
        ),
        "com.example.lib.SomeClass": CodeData(
            type="class", repo="test", file_path=Path("com/example/lib/test.kt"), name="SomeClass", source_code=""
        ),
        "com.example.MyType": CodeData(
            type="class", repo="test", file_path=Path("com/example/test.kt"), name="MyType", source_code=""
        ),
        "com.example.MyAnnotation": CodeData(
            type="annotation", repo="test", file_path=Path("com/example/test.kt"), name="MyAnnotation", source_code=""
        ),
        "com.example.getMyClass": CodeData(
            type="function", repo="test", file_path=Path("com/example/test.kt"), name="getMyClass", source_code=""
        ),
        "com.example.MyInterface": CodeData(
            type="interface", repo="test", file_path=Path("com/example/test.kt"), name="MyInterface", source_code=""
        ),
    }


@pytest.fixture
def sample_imports_context() -> dict[str, str]:
    return {
        "ParentClass": "com.example.ParentClass",
        "MyClass": "com.example.MyClass",
        "SomeClass": "com.example.lib.SomeClass",
        "MyType": "com.example.MyType",
        "MyAnnotation": "com.example.MyAnnotation",
        "getMyClass": "com.example.getMyClass",
        "MyInterface": "com.example.MyInterface",
    }


def test_class_inheritance_single_parent(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of single class inheritance in Kotlin."""

    file_path = Path("test/test_file.kt")
    code = """
class ChildClass : ParentClass() {
}
    """
    detector._extract_imports_context = lambda _: sample_imports_context

    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    parent_data = sample_code_data["com.example.ParentClass"]
    assert len(parent_data.references) == 2  # noqa: PLR2004
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == "class ChildClass : ParentClass() {\n}"


def test_class_inheritance_multiple_interfaces(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of class implementing multiple interfaces."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
class MyClass : ParentClass(), MyInterface {
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should detect ParentClass reference
    parent_data = sample_code_data["com.example.ParentClass"]
    assert len(parent_data.references) == 2  # noqa: PLR2004
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == "class MyClass : ParentClass(), MyInterface {\n}"

    # Should detect MyInterface reference
    interface_data = sample_code_data["com.example.MyInterface"]
    assert len(interface_data.references) == 2  # noqa: PLR2004
    assert interface_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == "class MyClass : ParentClass(), MyInterface {\n}"


def test_class_inheritance_same_file(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of inheritance within the same file."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
open class ParentClass {
}

class MyClass : ParentClass() {
}
"""
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should detect ParentClass reference
    parent_data = sample_code_data["com.example.ParentClass"]
    assert len(parent_data.references) == 2  # noqa: PLR2004
    assert parent_data.references[0].type == ReferenceType.INHERITANCE
    assert parent_data.references[0].text == "class MyClass : ParentClass() {\n}"


def test_function_call_simple(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple function calls."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    MyClass()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == "MyClass()"


def test_function_call_method_chaining(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of method chaining calls."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    getMyClass().someMethod()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    function_data = sample_code_data["com.example.getMyClass"]
    assert len(function_data.references) == 1
    assert function_data.references[0].type == ReferenceType.CALL
    assert function_data.references[0].text == "getMyClass()"


def test_type_annotation_property(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of type annotations in property declarations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
class TestClass {
    val myProperty: MyType = MyType()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    # Should find both type annotation and constructor call
    assert len(type_data.references) == 2  # noqa: PLR2004
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"
    assert type_data.references[1].type == ReferenceType.CALL
    assert type_data.references[1].text == "MyType()"


def test_type_annotation_function_parameter(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of type annotations in function parameters."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun processData(param: MyType): MyType {
    return param
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    # Should find type annotations for both parameter and return type
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"


def test_type_annotation_generic(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of generic type annotations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun processList(items: List<MyType>): List<MyType> {
    return items
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"


def test_attribute_access_property(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of property access."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val value = MyClass.staticProperty
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.ATTRIBUTE_ACCESS
    assert class_data.references[0].text == "MyClass.staticProperty"


def test_method_call_on_object(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of method calls on objects."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    MyClass.staticMethod()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # Should detect both function call and attribute access
    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.ATTRIBUTE_ACCESS
    assert class_data.references[0].text == "MyClass.staticMethod"


def test_annotation_simple(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of simple annotations."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
@MyAnnotation
class TestClass {
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    annotation_data = sample_code_data["com.example.MyAnnotation"]
    assert len(annotation_data.references) == 2  # noqa: PLR2004
    assert annotation_data.references[0].type == ReferenceType.DECORATOR
    assert annotation_data.references[0].text == "@MyAnnotation"


def test_annotation_with_parameters(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of annotations with parameters."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
@MyAnnotation("test")
fun testFunction() {
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    annotation_data = sample_code_data["com.example.MyAnnotation"]
    assert len(annotation_data.references) == 2  # noqa: PLR2004
    assert annotation_data.references[0].type == ReferenceType.DECORATOR
    assert annotation_data.references[0].text == '@MyAnnotation("test")'


def test_assignment_property_initialization(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of assignment in property initialization."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
class TestClass {
    val instance = MyClass()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == "MyClass()"


def test_assignment_variable(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of assignment to variable."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val myVar = MyClass()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == "MyClass()"


def test_companion_object_access(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of companion object access."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val instance = MyClass.create()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.ATTRIBUTE_ACCESS
    assert class_data.references[0].text == "MyClass.create"


def test_extension_function_call(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of extension function usage."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val obj = MyClass()
    obj.extensionMethod()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    class_data = sample_code_data["com.example.MyClass"]
    assert len(class_data.references) == 1
    assert class_data.references[0].type == ReferenceType.CALL
    assert class_data.references[0].text == "MyClass()"


def test_no_reference_when_not_found(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test that no reference is created when identifier is not found."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    UnknownClass()
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # No references should be added to any CodeData objects
    for code_data in sample_code_data.values():
        assert len(code_data.references) == 0


def test_when_expression_type_check(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of type references in when expressions."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun processValue(obj: Any) {
    when (obj) {
        is MyType -> println("MyType")
        else -> println("Other")
    }
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"


def test_data_class_usage(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of data class constructor calls."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val data = MyType(field = "value")
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.CALL
    assert type_data.references[0].text == 'MyType(field = "value")'


def test_lambda_with_type_annotation(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test detection of type annotations in lambda expressions."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
fun main() {
    val lambda: (MyType) -> MyType = { param -> param }
}
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    type_data = sample_code_data["com.example.MyType"]
    assert len(type_data.references) == 1
    assert type_data.references[0].type == ReferenceType.TYPE_ANNOTATION
    assert type_data.references[0].text == "MyType"


def test_unsupported_node_type(
    detector: KotlinReferenceDetector, sample_code_data: dict[str, CodeData], sample_imports_context: dict[str, str]
) -> None:
    """Test handling of unsupported node types."""
    detector._extract_imports_context = lambda _: sample_imports_context

    file_path = Path("test/test_file.kt")
    code = """
// This is a comment that will create an unsupported node type
/* Block comment */
    """
    node = get_parser("kotlin").parse(code.encode()).root_node
    detector._find_references_in_file(file_path, code, node, sample_code_data)

    # No references should be added
    for code_data in sample_code_data.values():
        assert len(code_data.references) == 0
