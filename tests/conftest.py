"""The session fixtures of the template tests: the working tree's snapshot and each variant
rendered once, when a test first reads it."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

# Before the first import of helpers, so its asserts fail with the values they compared, as
# a test module's do.
pytest.register_assert_rewrite("helpers")

from helpers import ROOT, VARIANTS, generate  # noqa: E402


@pytest.fixture(scope="session")
def template_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A snapshot of the working tree, so uncommitted template changes are what is tested."""
    src = tmp_path_factory.mktemp("template-src")
    shutil.copy(ROOT / "copier.yml", src / "copier.yml")
    shutil.copytree(ROOT / "template", src / "template")
    return src


@pytest.fixture(scope="session")
def render(template_src: Path, tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Path]:
    """Each variant rendered once per session, when a test first reads it. The renders are
    shared: a test reads them and writes nothing into them."""
    renders: dict[str, Path] = {}

    def get(name: str) -> Path:
        if name not in renders:
            dst = tmp_path_factory.mktemp(name) / "repo"
            renders[name] = generate(template_src, dst, **VARIANTS[name])
        return renders[name]

    return get


@pytest.fixture(params=list(VARIANTS), scope="session")
def variant(request: pytest.FixtureRequest, render: Callable[[str], Path]) -> tuple[str, Path]:
    """A check that differs between variants, run on each render."""
    return request.param, render(request.param)


@pytest.fixture(scope="session")
def keyed_nested(render: Callable[[str], Path]) -> Path:
    """The render a check no answer changes reads."""
    return render("keyed-nested")


@pytest.fixture(scope="session")
def keyless_flat(render: Callable[[str], Path]) -> Path:
    return render("keyless-flat")


@pytest.fixture(scope="session")
def tenants(render: Callable[[str], Path]) -> Path:
    """The multi-tenant render with a write server and basic auth (#174)."""
    return render("tenants")


@pytest.fixture(scope="session")
def tenants_keyless(render: Callable[[str], Path]) -> Path:
    """The multi-tenant render whose tenants hold a credential that is no key (#207)."""
    return render("tenants-keyless")
