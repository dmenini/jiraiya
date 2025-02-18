from pathlib import Path

import pytest

from doc_scribe.io.code_loader import CodebaseLoader


@pytest.fixture
def temp_codebase(tmp_path: Path) -> Path:
    (tmp_path / "module1").mkdir()
    (tmp_path / "module2").mkdir()
    (tmp_path / "module1" / "file1.py").write_text("print('Hello from module1')")
    (tmp_path / "module2" / "file2.py").write_text("print('Hello from module2')")
    (tmp_path / "module2" / "file3.kt").write_text("fun main() { println('Hello from Kotlin') }")
    return tmp_path


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    temp_file = tmp_path / "mock_file.py"
    temp_file.write_text("print('mocked')")
    return temp_file


@pytest.fixture
def loader(temp_codebase: Path) -> CodebaseLoader:
    return CodebaseLoader(root_path=temp_codebase)


def test_get_all_files(loader: CodebaseLoader, temp_codebase: Path) -> None:
    files = loader._get_file_paths()
    expected_files = {
        temp_codebase / "module1" / "file1.py",
        temp_codebase / "module2" / "file2.py",
        temp_codebase / "module2" / "file3.kt",
    }
    assert set(files) == expected_files


def test_load_file(loader: CodebaseLoader, temp_file: Path) -> None:
    code = loader.load_file(temp_file)
    assert code == "print('mocked')"


def test_load_all_files(loader: CodebaseLoader) -> None:
    loaded_files = loader.load_all_files()
    assert "module1/file1.py" in loaded_files
    assert "module2/file2.py" in loaded_files
    assert "module2/file3.kt" in loaded_files


def test_load_all_modules(loader: CodebaseLoader) -> None:
    modules = loader.load_all_modules()
    assert "module1" in modules
    assert "module2" in modules
    assert "module2" in modules
    assert "Hello from Kotlin" in modules["module2"]


def test_exclude_files(loader: CodebaseLoader, temp_codebase: Path) -> None:
    loader = CodebaseLoader(root_path=temp_codebase, exclude=["module2"])
    loaded_files = loader.load_all_files()
    assert "module1/file1.py" in loaded_files
    assert "module2/file2.py" not in loaded_files


def test_include_files(loader: CodebaseLoader, temp_codebase: Path) -> None:
    loader = CodebaseLoader(root_path=temp_codebase, include=["module1"])
    loaded_files = loader.load_all_files()
    assert "module1/file1.py" in loaded_files
    assert "module2/file2.py" not in loaded_files


def test_load_formatted_file_content(loader: CodebaseLoader, temp_file: Path) -> None:
    formatted_content = loader._load_formatted_file_content(temp_file)
    assert formatted_content.startswith("# File: mock_file.py\n\n")
    assert "print('mocked')" in formatted_content
