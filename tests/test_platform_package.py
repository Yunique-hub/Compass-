import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_platform_package.py"
SPEC = importlib.util.spec_from_file_location("validate_platform_package", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_zip(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def valid_files():
    root = "compass-student-growth"
    return {
        f"{root}/SKILL.md": "---\nname: compass-student-growth\ndescription: test\n---\n",
        f"{root}/manifest.yaml": "name: compass-student-growth\nversion: 3.4.0\nscope: private\n",
        f"{root}/agents/openai.yaml": (
            "interface:\n"
            "  display_name: test\n"
            "  default_prompt: Use $compass-student-growth for this task.\n"
        ),
    }


def test_wrapped_platform_package_is_valid(tmp_path):
    package = tmp_path / "valid.zip"
    write_zip(package, valid_files())
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is True
    assert result["errors"] == []


def test_flat_package_is_rejected(tmp_path):
    package = tmp_path / "flat.zip"
    files = {name.split("/", 1)[1]: content for name, content in valid_files().items()}
    write_zip(package, files)
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is False
    assert any("expected one root" in error for error in result["errors"])


def test_wrong_version_is_rejected(tmp_path):
    package = tmp_path / "wrong-version.zip"
    files = valid_files()
    files["compass-student-growth/manifest.yaml"] = (
        "name: compass-student-growth\nversion: 3.3.1\nscope: private\n"
    )
    write_zip(package, files)
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is False
    assert any("manifest version" in error for error in result["errors"])


def test_unsafe_path_is_rejected(tmp_path):
    package = tmp_path / "unsafe.zip"
    files = valid_files()
    files["compass-student-growth/../escape.txt"] = "bad"
    write_zip(package, files)
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is False
    assert any("unsafe path" in error for error in result["errors"])


def test_development_files_are_rejected(tmp_path):
    package = tmp_path / "development-files.zip"
    files = valid_files()
    files["compass-student-growth/tests/test_example.py"] = "assert True\n"
    write_zip(package, files)
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is False
    assert any("development-only files" in error for error in result["errors"])


def test_agents_prompt_must_reference_skill(tmp_path):
    package = tmp_path / "bad-agents.zip"
    files = valid_files()
    files["compass-student-growth/agents/openai.yaml"] = "interface:\n  default_prompt: test\n"
    write_zip(package, files)
    result = MODULE.validate(package, "compass-student-growth", "3.4.0")
    assert result["valid"] is False
    assert any("default_prompt" in error for error in result["errors"])
