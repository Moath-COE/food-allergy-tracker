"""The project's pytest configuration (pyproject.toml), exercised on a throwaway test file."""

import subprocess
import sys
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

SAMPLE = """
import pytest

@pytest.mark.llm
def test_llm_eval():
    pass

def test_plain():
    pass
"""


def run_pytest(tmp_path: Path, source: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "test_sample.py").write_text(source)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(PYPROJECT),
            f"--rootdir={tmp_path}",
            "-p",
            "no:cacheprovider",
            str(tmp_path / "test_sample.py"),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_llm_marked_tests_are_deselected_by_default(tmp_path: Path) -> None:
    result = run_pytest(tmp_path, SAMPLE)

    assert result.returncode == 0, result.stdout
    assert "1 passed, 1 deselected" in result.stdout


def test_llm_marked_tests_run_when_selected_with_m_llm(tmp_path: Path) -> None:
    result = run_pytest(tmp_path, SAMPLE, "-m", "llm", "-v")

    assert result.returncode == 0, result.stdout
    assert "test_llm_eval PASSED" in result.stdout
    assert "1 deselected" in result.stdout


def test_unregistered_marker_is_an_error(tmp_path: Path) -> None:
    source = "import pytest\n\n@pytest.mark.not_a_marker\ndef test_x():\n    pass\n"

    result = run_pytest(tmp_path, source)

    assert result.returncode != 0
    assert "not_a_marker" in result.stdout + result.stderr
