#!/usr/bin/env bash
# Prove the template: generate a throwaway source repository from the WORKING TREE and
# run the full check suite on it (uv sync, ruff, mypy, pytest with core's family check,
# pre-commit), then require refresh_reference.py, with no list declared, to refuse to run
# and write nothing, require core's frame to refuse refresh_upstream.py while it has no
# pages, and run
# the sibling check where the import path nests (none renders where it is flat): with the
# wheel alone, failing on a conflicting requirement, warning on a sibling on another core
# minor and on one that pins this package's previous minor, and failing on one that pins a
# later minor; require parse/ and tests/fixtures/files/ exactly where has_files is true;
# check offline that a task named in BULK_TASKS gets no tool and no route, that the
# refresh script on core's frame renders a value list and an id list into one enums.py, as
# ruff leaves it, and that it sends each request once, counts it, one that fails in
# transport too, and keeps the lists --only leaves out;
# require none of the reference scaffold where has_reference_data is false; and prove the
# package contract offline: mcp.py exports build, SOURCE and ENV_VARS, and a server a host
# builds from build()'s tool set with register_tasks serves the tools, caps and option
# defaults of the entry point, the write server's too where there is one, which core's one
# entry holds to loopback and which passes core's assert_write_tools on a task that returns
# the scaffold's WritePreview, and in the multi-tenant shape the bound server of --<param>
# as well, whose instructions say that no tool takes the tenant. In the general shape, the
# general part of a repository without tasks and servers (ADR-0003), it requires none of a
# source's 25 other files and none of the seven answers of an upstream, the repository's name
# in the answers and the manifest, and, as the answers record the package's key, a
# _client.py whose ENV_VARS declares that key and that holds no client, beside core's
# built-answer check, which passes on the render, or neither where the package holds no key
# (sdk-core#538, ADR-0003), and runs the checks of the render and the sibling check.
# No GitHub involved. The placeholder key is core's plugin's to guarantee, and its own
# suite tests it. --all proves every shape of the list `shapes` below, the keyless nested
# one again with -d has_files=true, a source that parses the files it downloads
# (sdk-core ADR-0020), and the template's CI runs --all. It generates with `copier copy`
# alone, as README.md says a source is generated.
#
# usage: scripts/prove.sh [--dest DIR] [--core-ref REF]
#                         [--keyless | --keyless-nested | --tenants | --general
#                          | --general-flat] [--keep]
#                         [-d key=value ...]
#        scripts/prove.sh --all [--core-ref REF] [--keep]
#   --all              every shape of the list `shapes`, one proof each in a process of its
#                      own, going on after a proof that failed; names each that failed and
#                      fails where one fails
#   --dest DIR         where to generate, a path that does not exist yet; default a new
#                      temporary directory
#   --core-ref REF     sdk-core commit to depend on, main or a full SHA; default "", the
#                      release on PyPI that core_version names, e.g. --core-ref main to prove
#                      against unreleased core
#   (no shape flag)    a keyed nested source, sdk-example-api (xippios.example.api)
#   --keyless          a keyless flat source, sdk-example (xippios.example)
#   --keyless-nested   a keyless nested source, sdk-example-files (xippios.example.files)
#   --tenants          a nested multi-tenant source with a write server and a key per tenant,
#                      sdk-example-tenants (xippios.example.tenants), its tenants' keys
#                      EXAMPLE_<NAME>_API_KEY under a prefix other than the slug's:
#                      write_server, tenant_param=org, no reference data
#   --general          the general shape, a publisher's shared package with a nested import
#                      path that holds its sources' key, sdk-example-shared
#                      (xippios.example.shared): api_key_env=EXAMPLE_API_KEY
#   --general-flat     the general shape, flat, in a repository not named sdk-<slug>, whose
#                      package holds no key, xippios-example (xippios.example)
#   --keep             leave the generated repository in place
#   -d key=value       one more copier answer, e.g. -d has_files=true, or
#                      -d has_reference_data=false for a source that packages none
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest=""
core_ref=""
shape=keyed
keep=0
all=0
extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --all) all=1 ;;
    --dest) dest="$2"; shift ;;
    --core-ref) core_ref="$2"; shift ;;
    --keyless) shape=keyless ;;
    --keyless-nested) shape=keyless-nested ;;
    --tenants) shape=tenants ;;
    --general) shape=general ;;
    --general-flat) shape=general-flat ;;
    --keep) keep=1 ;;
    -d) extra+=(-d "$2"); shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
# Every shape of the family, one proof each, in the order --all runs them: the arguments
# that make the proof, its shape's flag and any answer it adds.
shapes=(
  ""
  "--keyless"
  "--keyless-nested"
  "--keyless-nested -d has_files=true"
  "--tenants"
  "--general"
  "--general-flat"
)
if [ "$all" = 1 ]; then
  if [ -n "$dest" ] || [ "$shape" != keyed ] || [ "${#extra[@]}" -gt 0 ]; then
    echo "error: --all takes --core-ref and --keep alone: each shape is generated apart" >&2
    exit 2
  fi
  passed=(--core-ref "$core_ref")
  if [ "$keep" = 1 ]; then passed+=(--keep); fi
  failed=()
  for n in "${!shapes[@]}"; do
    read -r -a flags <<< "${shapes[$n]}"
    proof="scripts/prove.sh${shapes[$n]:+ ${shapes[$n]}}"
    echo "==> proof $((n + 1)) of ${#shapes[@]}: $proof"
    "$here/scripts/prove.sh" "${flags[@]}" "${passed[@]}" || failed+=("$proof")
    echo
  done
  if [ "${#failed[@]}" -gt 0 ]; then
    echo "==> ${#failed[@]} of ${#shapes[@]} proofs failed" >&2
    printf 'failed: %s\n' "${failed[@]}" >&2
    exit 1
  fi
  echo "==> all ${#shapes[@]} proofs passed"
  exit 0
fi
# The keyed slug nests (example-api → xippios.example.api) so the proof covers
# sdk-core ADR-0006; a keyless one is flat or nested.
name="Example Data Service"
case "$shape" in
  keyless) slug="example"; key=() ;;
  keyless-nested) slug="example-files"; key=() ;;
  tenants) slug="example-tenants"; key=(-d "api_key_env=EXAMPLE_API_KEY"
    -d "write_server=true" -d "tenant_param=org" -d "has_reference_data=false") ;;
  general) slug="example-shared"; name="Shared code of the example sources"
    key=(-d "shape=general" -d "api_key_env=EXAMPLE_API_KEY") ;;
  general-flat) slug="example"; name="Example tools"
    key=(-d "shape=general" -d "repository_name=xippios-example") ;;
  *) slug="example-api"; key=(-d "api_key_env=EXAMPLE_API_KEY") ;;
esac
# The repository's name: sdk-<slug>, or the answer of a repository named otherwise; and the
# key the answers give, empty for none.
repository="sdk-$slug"
given_key=""
for arg in "${key[@]}" "${extra[@]}"; do
  case "$arg" in
    repository_name=*) repository="${arg#repository_name=}" ;;
    api_key_env=*) given_key="${arg#api_key_env=}" ;;
  esac
done
if [ -n "$dest" ] && [ -e "$dest" ]; then
  echo "error: --dest $dest already exists" >&2
  exit 2
fi
work="$(mktemp -d "${TMPDIR:-/tmp}/sdk-template-prove.XXXXXX")"
dest="${dest:-$work/$repository}"

# Snapshot the working tree so uncommitted template changes are what gets proven. The
# snapshot is a git repository tagged with the version of the CHANGELOG's top release
# heading, so the generated .copier-answers.yml names a template tag (_commit: vX.Y.Z), as
# a repository generated from a template release does and as core's family check requires.
snapshot="$work/template-src"
mkdir -p "$snapshot"
cp -r "$here/copier.yml" "$here/template" "$snapshot/"
version="$(sed -nE 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - .*/\1/p' "$here/CHANGELOG.md" | head -n 1)"
git -C "$snapshot" init -q -b main
git -C "$snapshot" add -A
git -C "$snapshot" -c user.name=prove -c user.email=prove@example.invalid \
  -c commit.gpgsign=false commit -q --no-verify -m "the working tree of sdk-template"
git -C "$snapshot" -c tag.gpgsign=false tag "v$version"

# Generate as a source is generated, with copier alone: from the snapshot at its tag, every
# answer given and the rest at their defaults, as the README's call does.
echo "==> generating $dest from the working tree at v$version"
uv run --project "$here" copier copy --defaults --quiet --vcs-ref "v$version" \
  -d "source_slug=$slug" \
  -d "source_name=$name" \
  -d "upstream_url=https://api.example.org" \
  -d "upstream_docs_url=https://api.example.org/docs" \
  "${key[@]}" \
  -d "core_git_ref=$core_ref" \
  "${extra[@]}" \
  "$snapshot" "$dest"

echo
echo "==> the checks of the render: uv sync, ruff, mypy, pytest, pre-commit"
(
  cd "$dest"
  uv sync --all-extras
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy
  uv run pytest
  git init -q -b main
  git add -A
  uv run pre-commit run --all-files
)

# Nested or flat as copier recorded it, so a -d import_path=... answer is proven as rendered.
import_path="$(sed -n 's/^import_path: //p' "$dest/.copier-answers.yml")"
package_dir="src/xippios/${import_path//.//}"

# The shape as copier recorded it: a source, or the general part of a repository alone, which
# renders none of a source's files and none of the checks below that read them (ADR-0003).
recorded_shape="$(sed -n 's/^shape: //p' "$dest/.copier-answers.yml")"
# The reference scaffold, as copier recorded has_reference_data (#40): whole, or none of it.
has_reference_data="$(sed -n 's/^has_reference_data: //p' "$dest/.copier-answers.yml")"
echo
if [ "$recorded_shape" = general ]; then
  echo "==> the general shape: none of a source's 25 other files, nothing of an upstream asked"
  for rel in "$package_dir/errors.py" "$package_dir/models.py" \
    "$package_dir/api" "$package_dir/parse" "$package_dir/tasks.py" "$package_dir/tasks_write.py" \
    "$package_dir/mcp.py" "$package_dir/mcp_write.py" "$package_dir/http.py" \
    "$package_dir/params.py" "$package_dir/enums.py" "$package_dir/reference" \
    scripts/refresh_reference.py scripts/refresh_upstream.py docs/upstream .gitattributes \
    .github/workflows/live.yml .claude/commands/add-endpoint.md \
    .claude/commands/record-fixture.md .claude/commands/refresh-upstream.md \
    .claude/commands/refresh-reference-data.md tests/test_family.py \
    tests/test_live.py tests/test_tasks.py tests/fixtures; do
    [ ! -e "$dest/$rel" ] || { echo "error: the general shape rendered $rel" >&2; exit 1; }
  done
  for answer in upstream_url upstream_docs_url write_server tenant_param \
    live_secrets has_files has_reference_data; do
    if grep -q "^$answer:" "$dest/.copier-answers.yml"; then
      echo "error: the general shape recorded $answer" >&2
      exit 1
    fi
  done
  grep -qx "repository_name: $repository" "$dest/.copier-answers.yml" \
    || { echo "error: the answers name no repository $repository" >&2; exit 1; }
  grep -qx "Homepage = \"https://github.com/xippios/$repository\"" "$dest/pyproject.toml" \
    || { echo "error: pyproject.toml names another repository" >&2; exit 1; }
  echo "none of them; the answers name the repository $repository, as pyproject.toml does"

  # The package's key, which both shapes ask, as copier recorded it, '' for none: it decides
  # the client file (sdk-core#538) and the built-answer check beside it (ADR-0003, decision 11).
  recorded_key="$(sed -n 's/^api_key_env: //p' "$dest/.copier-answers.yml")"
  [ "$recorded_key" = "${given_key:-''}" ] \
    || { echo "error: the answers record api_key_env: $recorded_key" >&2; exit 1; }
  echo
  if [ -z "$given_key" ]; then
    echo "==> the package holds no key, so neither _client.py nor the built-answer check rendered"
    for rel in "$package_dir/_client.py" tests/test_built_answers.py; do
      [ ! -e "$dest/$rel" ] \
        || { echo "error: a package without a key rendered $rel" >&2; exit 1; }
    done
    echo "neither"
  else
    echo "==> the package holds a key: _client.py declares it in ENV_VARS and holds no client"
    (cd "$dest" && uv run python - "xippios.$import_path" "$given_key" <<'PY'
import importlib
import sys

from xippios.core import AsyncClient, ClientConfig, EnvVar

package, key = sys.argv[1], sys.argv[2]
client = importlib.import_module(f"{package}._client")
assert client.ENV_VARS == (EnvVar(key, secret=True, required=True),), client.ENV_VARS
held = [name for name, value in vars(client).items() if isinstance(value, AsyncClient | ClientConfig)]
assert held == [], held
print(f"ENV_VARS = {client.ENV_VARS!r}; no client and no client's configuration")
PY
    )
    echo
    echo "==> the package holds a key: core's built-answer check, collected, passes on the render"
    (cd "$dest" && uv run pytest -q tests/test_built_answers.py)
  fi
elif [ "$has_reference_data" = true ]; then
  # Core's frame stops before anything is read or written while LISTS declares no list.
  echo "==> refresh_reference.py, with no list declared, refuses to run and writes nothing"
  if (cd "$dest" && uv run python scripts/refresh_reference.py --render-only) \
    2> "$work/reference.err"; then
    echo "error: refresh_reference.py ran with no list declared" >&2
    exit 1
  fi
  refusal="$(grep "Nothing to fetch: declare the lists" "$work/reference.err")" \
    || { cat "$work/reference.err" >&2; exit 1; }
  (cd "$dest" && git diff --exit-code && test -z "$(git ls-files --others --exclude-standard)")
  echo "refused: $refusal"
else
  echo "==> has_reference_data: $has_reference_data, so none of the reference scaffold rendered"
  for rel in "$package_dir/params.py" "$package_dir/enums.py" "$package_dir/reference" \
    scripts/refresh_reference.py .claude/commands/refresh-reference-data.md; do
    [ ! -e "$dest/$rel" ] || { echo "error: $rel rendered without reference data" >&2; exit 1; }
  done
  echo "none of params.py, enums.py, reference/, refresh_reference.py, /refresh-reference-data"
fi

if [ "$recorded_shape" = source ]; then
  echo
  echo "==> refresh_upstream.py runs on core's frame, which refuses its SNAPSHOT until it has pages"
  if (cd "$dest" && uv run scripts/refresh_upstream.py --check) 2> "$work/refresh.err"; then
    echo "error: the declaration without pages ran" >&2
    exit 1
  fi
  refusal="$(grep "Nothing to fetch: declare the snapshot's pages" "$work/refresh.err")" \
    || { cat "$work/refresh.err" >&2; exit 1; }
  echo "refused: $refusal"
fi

# The parsers' package and the samples' table, as copier recorded has_files
# (sdk-core ADR-0020): the suite above passed on the render, with an empty parse/ where
# they are rendered.
has_files="$(sed -n 's/^has_files: //p' "$dest/.copier-answers.yml")"
parse_dir="$package_dir/parse"
echo
if [ "$has_files" = true ]; then
  echo "==> has_files: parse/ and tests/fixtures/files/README.md rendered, the suite passed"
  for rel in "$parse_dir/__init__.py" tests/fixtures/files/README.md; do
    [ -f "$dest/$rel" ] || { echo "error: has_files rendered no $rel" >&2; exit 1; }
  done
  (cd "$dest" && git ls-files "$parse_dir" tests/fixtures)
else
  echo "==> has_files: ${has_files:-not asked}, so neither parse/ nor tests/fixtures/ rendered"
  for rel in "$parse_dir" tests/fixtures; do
    [ ! -e "$dest/$rel" ] || { echo "error: $rel rendered without has_files" >&2; exit 1; }
  done
fi

echo
if [[ "$import_path" != *.* ]]; then
  echo "==> no sibling check where the import path is flat (xippios.$import_path)"
  if [ -e "$dest/.github/workflows/siblings.yml" ] || [ -e "$dest/.github/scripts" ]; then
    echo "error: a flat source renders the sibling check" >&2
    exit 1
  fi
  echo "neither .github/workflows/siblings.yml nor .github/scripts/ rendered"
else
  # XIPPIOS_SIBLINGS set and empty: the wheel alone, so the proof lists no repositories
  # on GitHub; the namespace levels, the import and the shipped files are checked as in CI.
  echo "==> .github/scripts/check-siblings.sh on the nested render (xippios.$import_path), the wheel alone"
  (cd "$dest" && XIPPIOS_SIBLINGS='' .github/scripts/check-siblings.sh)

  echo
  echo "==> the sibling check fails on a conflict that is not the core minor: httpx<0.20"
  if (cd "$dest" && XIPPIOS_SIBLINGS='httpx<0.20' .github/scripts/check-siblings.sh) \
    > "$work/conflict.log" 2>&1; then
    cat "$work/conflict.log" >&2
    echo "error: the sibling check passed a conflicting sibling" >&2
    exit 1
  fi
  if ! grep -qx "error: httpx<0.20 does not install beside this wheel" "$work/conflict.log"; then
    cat "$work/conflict.log" >&2
    exit 1
  fi
  echo "failed, as it must: $(tail -n 1 "$work/conflict.log")"

  # A sibling built here whose one release needs a core minor on PyPI that this wheel does
  # not take (0.2 beside 0.3, else 0.3; 0.1.0 is yanked): the check leaves it out with a
  # warning and passes.
  echo
  echo "==> a sibling on another core minor only is left out with a warning, never a failure"
  own_core="$("$dest/.venv/bin/python" -c \
    'from importlib.metadata import version; print(version("xippios-core"))')"
  case "$own_core" in
    0.3.*) other_core="0.2.0" ;;
    *) other_core="0.3.0" ;;
  esac
  other="$work/sdk-example-other"
  mkdir -p "$other/src/xippios/example/other"
  : > "$other/src/xippios/example/other/__init__.py"
  printf '%s\n' '[project]' 'name = "xippios-example-other"' 'version = "0.1.0"' \
    "dependencies = [\"xippios-core~=$other_core\"]" '' '[build-system]' \
    'requires = ["hatchling>=1.27"]' 'build-backend = "hatchling.build"' '' \
    '[tool.hatch.build.targets.wheel]' 'packages = ["src/xippios"]' > "$other/pyproject.toml"
  if ! (cd "$dest" && XIPPIOS_SIBLINGS="xippios-example-other @ file://$other" \
    .github/scripts/check-siblings.sh) > "$work/minor.log" 2>&1; then
    cat "$work/minor.log" >&2
    echo "error: the sibling check failed on a sibling on another core minor" >&2
    exit 1
  fi
  grep "^::warning::xippios-example-other" "$work/minor.log" \
    || { cat "$work/minor.log" >&2; exit 1; }

  # Two siblings built here that depend on this package, each beside a release of it that a
  # find-links directory holds as PyPI would: one pins its previous minor (0.0 beside 0.1),
  # which the check leaves out with a warning that names the pin, and passes; one pins a
  # later minor (0.2), which fails it.
  echo
  echo "==> a sibling that pins this package's previous minor is left out with a warning"
  own_version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$dest/pyproject.toml")"
  own_rest="${own_version#*.}"
  previous="${own_version%%.*}.$((${own_rest%%.*} - 1))"
  later="${own_version%%.*}.$((${own_rest%%.*} + 1))"
  # A project of one empty package: its directory under $work, its name, version and
  # dependencies, and its package's directory under src/.
  project() {
    mkdir -p "$work/$1/src/$5"
    : > "$work/$1/src/$5/__init__.py"
    printf '%s\n' '[project]' "name = \"$2\"" "version = \"$3\"" "dependencies = [$4]" '' \
      '[build-system]' 'requires = ["hatchling>=1.27"]' 'build-backend = "hatchling.build"' \
      '' '[tool.hatch.build.targets.wheel]' 'packages = ["src/xippios"]' \
      > "$work/$1/pyproject.toml"
  }
  for minor in "$previous" "$later"; do
    project "own-$minor" "xippios-$slug" "$minor.0" "" "xippios/${import_path//.//}"
    uv build --quiet --wheel --out-dir "$work/links" "$work/own-$minor"
  done
  project pinned xippios-example-pinned 0.1.0 "\"xippios-$slug~=$previous.0\"" \
    xippios/example/pinned
  project ahead xippios-example-ahead 0.1.0 "\"xippios-$slug~=$later.0\"" xippios/example/ahead
  if ! (cd "$dest" && UV_FIND_LINKS="$work/links" \
    XIPPIOS_SIBLINGS="xippios-example-pinned @ file://$work/pinned" \
    .github/scripts/check-siblings.sh) > "$work/pin.log" 2>&1; then
    cat "$work/pin.log" >&2
    echo "error: the sibling check failed on a sibling that pins the previous minor" >&2
    exit 1
  fi
  grep -F "::warning::xippios-example-pinned @ file://$work/pinned: pins xippios-$slug $previous.*" \
    "$work/pin.log" || { cat "$work/pin.log" >&2; exit 1; }

  echo
  echo "==> the sibling check fails on a sibling that pins a later minor of this package"
  if (cd "$dest" && UV_FIND_LINKS="$work/links" \
    XIPPIOS_SIBLINGS="xippios-example-ahead @ file://$work/ahead" \
    .github/scripts/check-siblings.sh) > "$work/ahead.log" 2>&1; then
    cat "$work/ahead.log" >&2
    echo "error: the sibling check passed a sibling that pins a later minor" >&2
    exit 1
  fi
  ahead_error="error: xippios-example-ahead @ file://$work/ahead does not install beside this wheel"
  if ! grep -qxF "$ahead_error" "$work/ahead.log"; then
    cat "$work/ahead.log" >&2
    exit 1
  fi
  echo "failed, as it must: $(tail -n 1 "$work/ahead.log")"
fi

if [ "$recorded_shape" = source ]; then
# Offline, on core's adapters as the render calls them: a task named in BULK_TASKS gets no
# tool and no route, while mcp.py passes tool_functions(tasks) and http.py tasks.__all__
# whole (sdk-core ADR-0040).
echo
echo "==> a bulk task gets no tool and no route; the adapters take tasks.__all__"
(cd "$dest" && uv run python - "xippios.$import_path" "$slug" <<'PY'
import asyncio
import importlib
import sys

package, slug = sys.argv[1], sys.argv[2]
tasks = importlib.import_module(f"{package}.tasks")


def get_example() -> str:
    """A task the adapters serve."""
    return "served"


def download_example() -> str:
    """A bulk task, Python-only."""
    return "a file"


for task in (get_example, download_example):
    task.__module__ = tasks.__name__
    setattr(tasks, task.__name__, task)
tasks.__all__ = ["get_example", "download_example"]
tasks.BULK_TASKS = frozenset({"download_example"})
server = importlib.import_module(f"{package}.mcp").server
tools = [tool.name for tool in asyncio.run(server.list_tools())]
routes = [route.path for route in importlib.import_module(f"{package}.http").router.routes]
assert tools == [f"{slug.replace('-', '_')}_get_example"], tools
assert routes == [f"/{slug}/get_example"], routes
print(f"tools {tools}, routes {routes}: download_example, in BULK_TASKS, neither")
PY
)

# Offline, on core's types as a host takes them (#81, #65): mcp.py exports build, SOURCE
# and ENV_VARS; a server a host builds with register_tasks from build()'s tool set and a
# second package's, a copy under another source, serves the tools, the caps and the
# option defaults that the entry point serves, the copy's alike under its own names, with
# a task, a cap of its own and an option of the source's put into tasks.py first; the same
# for the write server where it renders, and, for a multi-tenant source, for the server
# --<param> binds, which stops at startup when its tenant has no key. A bound server's
# instructions say nowhere that a tool takes the tenant's argument but in core's closing
# sentence (#219), the write server's entry refuses --http beyond loopback without
# --allow-remote, and it passes core's assert_write_tools as /add-endpoint calls it (#220),
# which holds the scaffold's WritePreview in every call (#271). Both servers are named
# xippios-<slug>. The entry point runs with its server's run() caught, so nothing is
# served.
echo
echo "==> the package contract: a host's server from build() serves what the entry point serves"
(cd "$dest" && uv run python - "xippios.$import_path" "$slug" <<'PY'
import argparse
import asyncio
import contextlib
import dataclasses
import importlib
import importlib.util
import io
import os
import re
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer
from xippios.core import EnvVar, Result, ResultCap, ResultMeta, TenantLock
from xippios.core.mcp import ToolSet, register_tasks
from xippios.core.testing import assert_write_tools, mcp_call_text

package, slug = sys.argv[1], sys.argv[2]
prefix = slug.replace("-", "_")
client = importlib.import_module(f"{package}._client")
tenants = getattr(client, "TENANTS", None)
param = None if tenants is None else tenants.param
takes = f"{param}: str, " if param else ""


def put(module_name: str, code: str, names: list[str], caps: dict[str, ResultCap]) -> None:
    """Define the tasks of ``code`` in the module, as a source's own tasks are defined there."""
    module = importlib.import_module(module_name)
    namespace: dict[str, Any] = {"Result": Result, "ResultMeta": ResultMeta}
    exec(code, namespace)  # the task's signature takes the tenant's parameter where there is one
    for name in names:
        namespace[name].__module__ = module.__name__
        setattr(module, name, namespace[name])
    module.__all__ = [*module.__all__, *names]
    module.MCP_CAPS = caps


put(
    f"{package}.tasks",
    f'''
def get_rows({takes.rstrip(", ")}) -> Result[list[int]]:
    """Five rows, which the tool's own cap cuts to two."""
    return Result[list[int]](data=list(range(5)), meta=ResultMeta(source={slug!r}, endpoint="x"))
''',
    ["get_rows"],
    {"get_rows": ResultCap(max_rows=2)},
)
tasks = importlib.import_module(f"{package}.tasks")


def mcp_add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--example-limit", type=int, default=5)


def mcp_apply_options(namespace: argparse.Namespace) -> None:
    seen["applied"] = namespace.example_limit


tasks.mcp_add_options = mcp_add_options
tasks.mcp_apply_options = mcp_apply_options

seen: dict[str, Any] = {}
parse_args = argparse.ArgumentParser.parse_args


def recording(self: argparse.ArgumentParser, *args: Any, **kwargs: Any) -> argparse.Namespace:
    parsed = parse_args(self, *args, **kwargs)
    seen["options"] = vars(parsed)
    return parsed


def caught(self: MCPServer, *args: Any, **kwargs: Any) -> None:
    seen["server"] = self


argparse.ArgumentParser.parse_args = recording  # type: ignore[method-assign]
MCPServer.run = caught  # type: ignore[method-assign]


def entry(module: Any, *argv: str) -> tuple[MCPServer, dict[str, Any]]:
    """The server the entry point runs, and the options it parsed from ``argv``."""
    seen.clear()
    sys.argv = [f"xippios-{slug}-mcp", *argv]
    module.run()
    return seen["server"], seen["options"]


def host_of(*tool_sets: ToolSet) -> MCPServer:
    """One server as a host builds it from tool sets, each one's hooks applied without options."""
    host = MCPServer("host")
    for tool_set in tool_sets:
        register_tasks(host, tool_set)
        if tool_set.apply_options is not None:
            tool_set.apply_options(tool_set.option_defaults())
    return host


def tools(server: MCPServer) -> dict[str, Any]:
    return {t.name: (t.input_schema, t.description) for t in asyncio.run(server.list_tools())}


def answers(server: MCPServer, arguments: dict[str, Any]) -> dict[str, str]:
    """Each tool's answer to ``arguments``, but the time each was retrieved, which differs."""
    return {
        name: re.sub(r'"retrieved_at":\s*"[^"]*"', "", asyncio.run(mcp_call_text(server, name, arguments)))
        for name in tools(server)
    }


def same(module: Any, tool_set: ToolSet, arguments: dict[str, Any], *argv: str) -> MCPServer:
    """A host's server of two packages, this one and a copy under another source (#81), and
    the entry point's serve the same tools, answers and options, the copy's under its own
    names with its own caps."""
    defaults = vars(tool_set.option_defaults())
    other = f"{prefix}_other_"
    host = host_of(tool_set, dataclasses.replace(tool_set, source=f"{slug}-other"))
    served, options = entry(module, *argv)

    def apart(found: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """This package's entries, and the copy's under this package's names."""
        mine = {name: value for name, value in found.items() if not name.startswith(other)}
        copy = {
            f"{prefix}_" + name.removeprefix(other): value
            for name, value in found.items()
            if name.startswith(other)
        }
        return mine, copy

    mine, copy = apart(tools(host))
    assert mine == copy == tools(served), (sorted(tools(host)), sorted(tools(served)))
    mine, copy = apart(answers(host, arguments))
    assert mine == copy == answers(served, arguments)
    bound = {param: argv[1] if argv else None} if param else {}
    assert options == {**defaults, **bound}, (options, defaults)
    return served


def bound_text(module: Any) -> str:
    """The instructions of the server ``--<param> demo`` binds, ``build(lock)``'s (#219): the
    unbound text says that a tool takes the tenant's argument, the bound one nowhere but in
    core's closing sentence, which names the tenant and says that no tool takes it."""
    takes = re.compile(rf"\btakes {param}\b")
    unbound = module.build().instructions
    assert takes.search(unbound), unbound
    text = module.build(TenantLock(tenants, client.DEMO)).instructions
    assert not takes.search(text), text
    assert text.endswith(f"bound to {param} {client.DEMO}; every tool acts on that {param} "
                         f"and takes no {param}."), text
    return text


mcp = importlib.import_module(f"{package}.mcp")
assert {"ENV_VARS", "SOURCE", "build", "server"} <= set(mcp.__all__), mcp.__all__
assert mcp.SOURCE == slug and mcp.ENV_VARS is client.ENV_VARS
assert all(isinstance(var, EnvVar) for var in mcp.ENV_VARS), mcp.ENV_VARS
tool_set = mcp.build()
assert isinstance(tool_set, ToolSet) and tool_set.read_only, tool_set
arguments = {param: "demo"} if param else {}
served = same(mcp, tool_set, arguments)
cut = asyncio.run(mcp_call_text(served, f"{prefix}_get_rows", arguments))
assert "narrow the query" in cut, cut
assert vars(tool_set.option_defaults())["example_limit"] == 5, "the source's option"
assert seen["applied"] == 5, "the entry point applied the source's option"
assert served.name == f"xippios-{slug}", served.name
print(f"{package}.mcp: {sorted(tools(served))} as a host serves them, the cap and options alike")

if param is not None:
    (field,) = tenants.fields  # API_KEY
    key = tenants.var(client.DEMO, field)
    os.environ[key] = "placeholder"  # pragma: allowlist secret (a stand-in)
    flag = f"--{param.replace('_', '-')}"
    bound = same(mcp, mcp.build(TenantLock(tenants, client.DEMO)), {}, flag, client.DEMO)
    assert param not in tools(bound)[f"{prefix}_get_rows"][0].get("properties", {}), "bound"
    print(f"{package}.mcp {flag} demo: {bound_text(mcp)!r}")
    del os.environ[key]
    os.environ[tenants.list_var] = "acme"
    refused = io.StringIO()
    with contextlib.redirect_stderr(refused), contextlib.suppress(SystemExit):
        entry(mcp, flag, "acme")
    assert tenants.var("acme", field) in refused.getvalue(), refused.getvalue()
    assert "server" not in seen, "stopped before a server ran"
    del os.environ[tenants.list_var]
    print(f"{flag} demo: bound as a host binds it; {flag} acme without its key: stopped")

if importlib.util.find_spec(f"{package}.mcp_write") is not None:
    put(
        f"{package}.tasks_write",
        f'''
from {package}.tasks_write import WritePreview


def create_row({takes}confirm: bool = False) -> Result[WritePreview | dict[str, bool]]:
    """Create a row, a preview unless confirm is true; the preview reads nothing."""
    meta = ResultMeta(source={slug!r}, endpoint="x")
    if confirm is not True:
        preview = WritePreview(endpoint="x", reads=[])
        return Result[WritePreview | dict[str, bool]](data=preview, meta=meta)
    return Result[WritePreview | dict[str, bool]](data={{"created": True}}, meta=meta)
''',
        ["create_row"],
        {},
    )
    mcp_write = importlib.import_module(f"{package}.mcp_write")
    write_set = mcp_write.build()
    assert not write_set.read_only, "a write server's tool set"
    served = same(mcp_write, write_set, arguments)
    assert served.name == f"xippios-{slug}", served.name
    refused = io.StringIO()
    with contextlib.redirect_stderr(refused), contextlib.suppress(SystemExit):
        entry(mcp_write, "--http", "--host", "0.0.0.0")
    assert "is a write server" in refused.getvalue(), refused.getvalue()
    assert "server" not in seen, "held to loopback: nothing served"
    assert list(tools(served)) == [f"{prefix}_create_row"], "write tools only"
    print(f"{package}.mcp_write: {sorted(tools(served))}, a write server as a host builds it")
    # The test /add-endpoint gives a source's first write task, as it calls it (#220), which
    # holds the preview's reads on the scaffold's WritePreview in every call (#271).
    tasks_write = importlib.import_module(f"{package}.tasks_write")
    http = importlib.import_module(f"{package}.http")
    asyncio.run(
        assert_write_tools(
            write_set,
            [getattr(tasks_write, name) for name in tasks_write.__all__],
            read_server=mcp.server,
            router=http.router,
        )
    )
    print(f"{package}.mcp_write: assert_write_tools(...) passed, held to loopback")
    if param is not None:
        print(f"{package}.mcp_write {flag} demo: {bound_text(mcp_write)!r}")
PY
)
fi

if [ "$has_reference_data" = true ]; then
# The refresh script's render on core's frame (sdk-core ADR-0062), with --render, the
# prefix of --render-only that core's parser takes, of two packaged lists fetched on
# different days, a value list and an id list whose names repeat: one enums.py of a
# StrEnum and an IntEnum, each with its date, as ruff leaves it (conventions §3,
# sdk-core ADR-0031), and a row of each in the provenance table of reference/README.md in
# place of the scaffold's "(none yet)", after its help, --he. The tree is restored after.
echo
echo "==> refresh_reference.py renders a value list and an id list into one enums.py"
(cd "$dest" && uv run python - "xippios.$import_path" <<'PY'
import dataclasses
import importlib
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

from xippios.core import PackagedList
from xippios.core.refresh import Enumeration, Listed

spec = importlib.util.spec_from_file_location("refresh", "scripts/refresh_reference.py")
assert spec is not None and spec.loader is not None
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
ids = Enumeration(ids="unitId", names="unitDescription")
script.LISTS = dataclasses.replace(
    script.LISTS,
    lists=(
        Listed("state_alpha", list, endpoint="get_param_values", enum=Enumeration()),
        Listed("unitsOfMeasure", list, endpoint="GetUnitsOfMeasure", enum=ids),
    ),
    packaged=("state_alpha", "unitsOfMeasure"),
)
reference = Path(importlib.import_module(sys.argv[1]).__file__).parent / "reference"
for param, endpoint, day, records in [
    ("state_alpha", "get_param_values", 25, [{"state_alpha": "AK"}, {"state_alpha": "C\u00f4te"}]),
    ("unitsOfMeasure", "GetUnitsOfMeasure", 23, [{"unitId": 33, "unitDescription": "Crates"},
                                                 {"unitId": 105, "unitDescription": "Crates"}]),
]:
    fetched = datetime(2026, 10, day, 9, 15, tzinfo=UTC)
    listed = PackagedList(param=param, endpoint=endpoint, fetched=fetched, records=records)
    listed.write(reference / f"{param}.json")
try:
    script.main(["--he"])
except SystemExit as exited:
    assert exited.code == 0, exited
else:
    raise AssertionError("--he printed no help")
assert script.main(["--render"]) == 0
enums = importlib.import_module(f"{sys.argv[1]}.enums")
assert enums.__all__ == ["StateAlpha", "UnitId"], enums.__all__
assert [enums.StateAlpha.AK, enums.StateAlpha.C_TE] == ["AK", "C\u00f4te"]
assert [enums.UnitId.CRATES_33, enums.UnitId.CRATES_105] == [33, 105]
assert "(fetched 2026-10-25)" in (enums.StateAlpha.__doc__ or "")
assert "(fetched 2026-10-23)" in (enums.UnitId.__doc__ or "")
rows = (reference / "README.md").read_text(encoding="utf-8")
assert "| `state_alpha.json` | `get_param_values` | 2026-10-25T09:15:00Z |" in rows, rows
assert "| `unitsOfMeasure.json` | `GetUnitsOfMeasure` | 2026-10-23T09:15:00Z |" in rows, rows
assert "(none yet)" not in rows, rows
PY
)
(cd "$dest" && uv run ruff format --check . && uv run ruff check . && git checkout -q -- . && git clean -fdq)

# Offline, through the package's own client, against answers respx replays (#64, #239):
# the refresh on core's frame sends each request once, a 503's included, and prints the
# requests it sent and the quota left, a failed run's too, a request that fails in
# transport counted as sent; --only fetches the named list alone and keeps the others'
# files, and refuses a name no packaged list has before any request. The tree is restored
# after.
echo
echo "==> refresh_reference.py sends each request once, counts it, and --only keeps the others"
(cd "$dest" && uv run python - "xippios.$import_path" <<'PY'
import contextlib
import dataclasses
import importlib
import importlib.util
import io
import os
import sys
from collections.abc import Callable, Coroutine, Sequence
from pathlib import Path
from typing import Any

import httpx
import respx
from xippios.core import TransportError, XippiosError
from xippios.core.refresh import Listed

package = importlib.import_module(f"{sys.argv[1]}._client")
key_env = getattr(package, "API_KEY_ENV", None)
if key_env:
    os.environ[key_env] = "placeholder"  # pragma: allowlist secret (a stand-in)
client = package.client
spec = importlib.util.spec_from_file_location("refresh", "scripts/refresh_reference.py")
assert spec is not None and spec.loader is not None
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
configured = client.config


def values(name: str) -> Callable[[], Coroutine[Any, Any, Sequence[dict[str, str]]]]:
    async def fetch() -> Sequence[dict[str, str]]:
        answer = await client.get_answer("/get_param_values", params={"param": name})
        return [{name: str(value)} for value in answer.payload]

    return fetch


packaged = ("state_alpha", "unit", "county")
script.LISTS = dataclasses.replace(
    script.LISTS,
    lists=tuple(Listed(name, values(name), endpoint="get_param_values") for name in packaged),
    packaged=packaged,
)
reference = Path(importlib.import_module(sys.argv[1]).__file__).parent / "reference"
files = {name: reference / f"{name}.json" for name in packaged}


def run(*args: str) -> tuple[str, BaseException | None]:
    """The script's main with ``args``: what it printed and what it raised, if anything."""
    out = io.StringIO()
    raised = None
    try:
        with contextlib.redirect_stdout(out):
            script.main(list(args))
    except (XippiosError, SystemExit) as error:
        raised = error
    assert client.config is configured, "the client's configuration restored"
    print(out.getvalue() + ("" if raised is None else f"{type(raised).__name__}: {raised}\n"))
    return out.getvalue(), raised


with respx.mock(base_url=package.BASE_URL) as upstream:
    route = upstream.get("/get_param_values")
    printed, raised = run("--help")
    assert isinstance(raised, SystemExit) and raised.code == 0, raised
    assert "--only" in printed and "--render-only" in printed, printed
    route.mock(return_value=httpx.Response(503))
    printed, raised = run()
    assert isinstance(raised, XippiosError), raised
    assert route.call_count == 1, f"one request, no retry: {route.call_count}"
    assert "requests sent: 1; quota left: not reported" in printed, printed
    assert not any(path.exists() for path in files.values()), "nothing written"
    # The third request gets no answer: it may have reached upstream, so it counts (#239).
    answers = [httpx.Response(200, json=["AK"]), httpx.Response(200, json=["CA"])]
    route.mock(side_effect=[*answers, httpx.ReadTimeout("no answer")])
    printed, raised = run()
    assert isinstance(raised, TransportError), raised
    assert route.call_count == 4, route.call_count
    sent = "requests sent: 3 (1 ended in a transport error, counted as sent); quota left:"
    assert sent in printed, printed
    assert not any(path.exists() for path in files.values()), "nothing written"
    quota = {"x-ratelimit-remaining": "41"}
    route.mock(return_value=httpx.Response(200, json=["AK", "CA"], headers=quota))
    printed, raised = run()
    assert raised is None, raised
    assert route.call_count == 7, route.call_count
    assert "requests sent: 3; quota left: 41 (x-ratelimit-remaining)" in printed, printed
    kept = {name: files[name].read_bytes() for name in ["state_alpha", "county"]}
    route.mock(return_value=httpx.Response(200, json=["MT"]))
    printed, raised = run("--only", "unit")
    assert raised is None, raised
    assert route.call_count == 8, route.call_count
    assert "requests sent: 1; quota left: not reported" in printed, printed
    assert {name: files[name].read_bytes() for name in kept} == kept, "--only keeps the others"
    assert '"MT"' in files["unit"].read_text()
    printed, raised = run("--only", "region")
    assert isinstance(raised, SystemExit), "--only took a list no packaged list has"
    assert route.call_count == 8, "refused before any request"
PY
)
(cd "$dest" && git checkout -q -- . && git clean -fdq)
fi

echo
echo "==> generated tree"
(cd "$dest" && git ls-files | sort)
if [ "$keep" = 1 ]; then
  echo "kept: $dest"
else
  rm -r "$work"
fi
