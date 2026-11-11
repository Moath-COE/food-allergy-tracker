"""The import-linter contracts in pyproject.toml (ARCHITECTURE section 4, ADR 0005).

Each case copies the source tree into a temp dir, adds (or appends to) a few modules, and runs
`lint-imports` there with the project's own contract config. A violating import must break
the named contract; the allowed imports must leave every contract kept. The cases of one test
run in parallel, one subprocess each.
"""

import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"

# A fragment of each contract's `name`, enough to tell the contracts apart.
DOMAIN = "domain imports nothing"
ANALYSIS = "analysis imports only domain"
CHANNELS_ONLY_MAIN = "only hassas.main imports hassas.channels"
NO_SDK = "no channel SDK is imported"
CHANNELS_IMPORT = "channels import only messaging"
DB = "core reaches the database only through hassas.db.repositories"
NO_MAIN = "nothing imports hassas.main"
AGENTS = "agents never import conversation or channels"
BENCHMARK = "benchmark imports only analysis"
ALL_CONTRACTS = [
    DOMAIN,
    ANALYSIS,
    CHANNELS_ONLY_MAIN,
    NO_SDK,
    CHANNELS_IMPORT,
    DB,
    NO_MAIN,
    AGENTS,
    BENCHMARK,
]

# path -> source. A path that already exists in the tree gets the source appended.
Files = dict[str, str]


@dataclass(frozen=True)
class Run:
    code: int
    verdicts: dict[str, str]  # contract fragment -> KEPT / BROKEN
    output: str


def lint(workdir: Path, files: Files) -> Run:
    """Run lint-imports on a copy of the tree in `workdir`, with `files` added."""
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(ROOT / "src" / "hassas", workdir / "hassas", ignore=ignore)
    shutil.copytree(ROOT / "benchmark", workdir / "benchmark", ignore=ignore)
    shutil.copy(ROOT / "pyproject.toml", workdir / "pyproject.toml")
    for relative, source in files.items():
        path = workdir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text() if path.exists() else ""
        path.write_text(existing + source)

    result = subprocess.run(
        [str(LINT_IMPORTS), "--config", str(workdir / "pyproject.toml"), "--no-cache"],
        capture_output=True,
        text=True,
        check=False,
        cwd=workdir,
        env={**os.environ, "PYTHONPATH": str(workdir)},
    )
    output = result.stdout + result.stderr
    flat = " ".join(output.split())  # contract names wrap across lines
    verdicts = {}
    for fragment in ALL_CONTRACTS:
        match = re.search(re.escape(fragment) + r".*?\b(KEPT|BROKEN)\b", flat)
        if match:
            verdicts[fragment] = match.group(1)
    return Run(result.returncode, verdicts, output)


def run_cases(tmp_path: Path, cases: dict[str, Files]) -> dict[str, Run]:
    def one(item: tuple[int, tuple[str, Files]]) -> tuple[str, Run]:
        index, (label, files) = item
        workdir = tmp_path / str(index)
        workdir.mkdir()
        return label, lint(workdir, files)

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(one, enumerate(cases.items())))


def assert_all_break(tmp_path: Path, contract: str, cases: dict[str, Files]) -> None:
    """Every case must break `contract` (and so fail the run)."""
    missed = [
        f"{label}\n{run.output}"
        for label, run in run_cases(tmp_path, cases).items()
        if run.code == 0 or run.verdicts.get(contract) != "BROKEN"
    ]
    assert not missed, f"cases that did not break '{contract}':\n" + "\n".join(missed)


def assert_all_kept(tmp_path: Path, contracts: list[str], cases: dict[str, Files]) -> None:
    """Every case must pass with every contract kept."""
    failed = [
        f"{label}\n{run.output}"
        for label, run in run_cases(tmp_path, cases).items()
        if run.code != 0 or any(run.verdicts.get(c) != "KEPT" for c in contracts)
    ]
    assert not failed, "cases that were not clean:\n" + "\n".join(failed)


# --- the clean tree ---


def test_all_contracts_are_kept_on_the_clean_tree(tmp_path: Path) -> None:
    run = lint(tmp_path, {})

    assert run.code == 0, run.output
    assert run.verdicts == dict.fromkeys(ALL_CONTRACTS, "KEPT"), run.output


# --- domain, analysis ---


def test_domain_cannot_import_other_hassas_packages(tmp_path: Path) -> None:
    sources = [
        "from hassas import messaging\n",
        "import hassas.analysis\n",
        "from hassas.db.repositories import users\n",
    ]
    cases = {
        source: {"hassas/domain/bad.py": source, "hassas/db/repositories/users.py": ""}
        for source in sources
    }

    assert_all_break(tmp_path, DOMAIN, cases)


def test_analysis_cannot_import_anything_but_domain(tmp_path: Path) -> None:
    sources = [
        "from hassas import messaging\n",
        "import hassas.config\n",
        "from hassas.db.repositories import users\n",
    ]
    cases = {
        source: {"hassas/analysis/bad.py": source, "hassas/db/repositories/users.py": ""}
        for source in sources
    }

    assert_all_break(tmp_path, ANALYSIS, cases)


# --- CH-1 ---


def test_CH_1_core_cannot_import_channels(tmp_path: Path) -> None:
    paths = [
        "hassas/conversation/bad.py",
        "hassas/agents/bad.py",
        "hassas/jobs/bad.py",
        "hassas/summary/bad.py",
        "hassas/messaging/bad.py",
        "hassas/db/bad.py",
        "hassas/health.py",
        "hassas/config.py",
        "hassas/new_top_level_module.py",
        "hassas/new_package/bad.py",
    ]
    cases = {
        path: {path: "from hassas.channels import fake\n", "hassas/new_package/__init__.py": ""}
        for path in paths
    }
    cases["a channel submodule"] = {
        "hassas/conversation/bad.py": "import hassas.channels.telegram\n"
    }
    cases["by way of another module"] = {
        "hassas/jobs/bad.py": "from hassas.conversation import relay\n",
        "hassas/conversation/relay.py": "from hassas.channels import fake\n",
    }

    assert_all_break(tmp_path, CHANNELS_ONLY_MAIN, cases)


def test_CH_1_main_may_import_channels(tmp_path: Path) -> None:
    cases = {
        "main": {
            "hassas/main.py": "from hassas.channels import fake\nimport hassas.channels.telegram\n"
        }
    }

    assert_all_kept(tmp_path, [CHANNELS_ONLY_MAIN], cases)


def test_CH_1_core_cannot_import_a_channel_sdk(tmp_path: Path) -> None:
    paths = [
        "hassas/conversation/bad.py",
        "hassas/jobs/bad.py",
        "hassas/config.py",
        "benchmark/bad.py",
        "hassas/new_top_level_module.py",
    ]
    cases = {path: {path: "import telegram\n"} for path in paths}
    cases["a submodule of the sdk"] = {
        "hassas/conversation/bad.py": "from telegram.ext import Application\n"
    }
    for sdk in ["aiogram", "telebot", "whatsapp", "pywa"]:
        cases[sdk] = {"hassas/conversation/bad.py": f"import {sdk}\n"}

    assert_all_break(tmp_path, NO_SDK, cases)


def test_CH_1_channels_may_import_a_channel_sdk(tmp_path: Path) -> None:
    cases = {
        "sdks": {
            "hassas/channels/telegram/client.py": "import telegram\n",
            "hassas/channels/fake/client.py": "from whatsapp import Client\n",
        }
    }

    assert_all_kept(tmp_path, [NO_SDK], cases)


def test_nothing_may_import_the_composition_root(tmp_path: Path) -> None:
    cases = {
        "from hassas import main": {"hassas/conversation/bad.py": "from hassas import main\n"},
        "import hassas.main": {"hassas/channels/bad.py": "import hassas.main\n"},
        "benchmark": {"benchmark/bad.py": "import hassas.main\n"},
    }

    assert_all_break(tmp_path, NO_MAIN, cases)


# --- channels' own imports ---


def test_channels_cannot_import_core_internals(tmp_path: Path) -> None:
    sources = [
        "from hassas.db.repositories import users\n",
        "import hassas.db\n",
        "import hassas.agents\n",
        "import hassas.analysis\n",
        "import hassas.jobs\n",
        "import hassas.summary\n",
        "import hassas.health\n",
        "import hassas.main\n",
        "import hassas.conversation.pipeline\n",
        "from hassas.conversation import pipeline\n",
        "import hassas.new_top_level_module\n",
    ]
    support = {
        "hassas/db/repositories/users.py": "",
        "hassas/conversation/pipeline.py": "",
        "hassas/new_top_level_module.py": "",
    }
    cases = {source: {"hassas/channels/telegram/bad.py": source, **support} for source in sources}
    cases["the channels package itself"] = {"hassas/channels/__init__.py": "import hassas.agents\n"}

    assert_all_break(tmp_path, CHANNELS_IMPORT, cases)


def test_channels_may_import_their_allowed_packages(tmp_path: Path) -> None:
    allowed = (
        "import hassas.messaging\n"
        "from hassas.messaging import something\n"
        "import hassas.domain\n"
        "import hassas.config\n"
        "import hassas.conversation\n"
        "from hassas.conversation import handle_message\n"
    )
    cases = {
        "allowed": {
            "hassas/channels/ok.py": allowed,
            "hassas/channels/telegram/ok.py": allowed,
            "hassas/channels/__init__.py": allowed,
            # the top-level conversation package imports its own submodules; that must not count
            "hassas/conversation/__init__.py": "from hassas.conversation import pipeline\n",
            "hassas/conversation/pipeline.py": "from hassas.db.repositories import users\n",
            "hassas/db/repositories/users.py": "",
        }
    }

    assert_all_kept(tmp_path, [CHANNELS_IMPORT], cases)


# --- the database ---

DB_FILES = {
    "hassas/db/models.py": "",
    "hassas/db/session.py": "",
    "hassas/db/new_db_module.py": "",
}


def test_core_cannot_import_db_internals(tmp_path: Path) -> None:
    cases = {
        f"{package} -> db.models": {
            f"hassas/{package}/bad.py": "from hassas.db.models import User\n",
            **DB_FILES,
        }
        for package in ["conversation", "agents", "jobs", "summary"]
    }
    for source in [
        "from hassas.db import models\n",
        "import hassas.db.session\n",
        "from hassas.db import new_db_module\n",
        "import hassas.db\n",
    ]:
        cases[source] = {"hassas/conversation/bad.py": source, **DB_FILES}
    cases["by way of a non-repository module"] = {
        "hassas/jobs/bad.py": "from hassas.db import mappers\n",
        "hassas/db/mappers.py": "from hassas.db import models\n",
        "hassas/db/models.py": "",
    }

    assert_all_break(tmp_path, DB, cases)


def test_core_may_import_db_repositories(tmp_path: Path) -> None:
    ok = "from hassas.db.repositories import users\nimport hassas.db.repositories\n"
    cases = {
        "repositories": {
            "hassas/conversation/ok.py": ok,
            "hassas/agents/ok.py": ok,
            "hassas/jobs/ok.py": ok,
            "hassas/summary/ok.py": ok,
            "hassas/conversation/__init__.py": "from hassas.db.repositories import users\n",
            # a repository may use the models and the session
            "hassas/db/repositories/users.py": "from hassas.db import models, session\n",
            "hassas/db/models.py": "",
            "hassas/db/session.py": "",
        }
    }

    assert_all_kept(tmp_path, [DB], cases)


# --- agents ---


def test_agents_cannot_import_conversation_or_channels(tmp_path: Path) -> None:
    sources = [
        "import hassas.conversation\n",
        "from hassas.conversation import pipeline\n",
        "from hassas.channels import fake\n",
        "import hassas.channels\n",
    ]
    cases = {
        source: {"hassas/agents/bad.py": source, "hassas/conversation/pipeline.py": ""}
        for source in sources
    }
    cases["by way of another module"] = {
        "hassas/agents/bad.py": "from hassas import jobs\n",
        "hassas/jobs/__init__.py": "from hassas import conversation\n",
    }

    assert_all_break(tmp_path, AGENTS, cases)


# --- benchmark ---


def test_benchmark_cannot_import_anything_but_analysis_and_domain(tmp_path: Path) -> None:
    sources = [
        "import hassas.messaging\n",
        "import hassas.config\n",
        "from hassas.db.repositories import users\n",
        "import hassas.agents\n",
        "import hassas\n",
        "import hassas.new_top_level_module\n",
    ]
    support = {"hassas/db/repositories/users.py": "", "hassas/new_top_level_module.py": ""}
    cases = {source: {"benchmark/bad.py": source, **support} for source in sources}

    assert_all_break(tmp_path, BENCHMARK, cases)


def test_benchmark_may_import_analysis_and_domain(tmp_path: Path) -> None:
    ok = "import hassas.analysis\nimport hassas.domain\nfrom hassas.analysis import engine\n"
    cases = {
        "analysis and domain": {
            "benchmark/__init__.py": ok,
            "benchmark/ok.py": ok,
            "hassas/analysis/engine.py": "from hassas.domain import types\n",
            "hassas/domain/types.py": "",
        }
    }

    assert_all_kept(tmp_path, [BENCHMARK, ANALYSIS], cases)
