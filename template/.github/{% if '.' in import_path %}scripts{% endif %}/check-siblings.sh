#!/usr/bin/env bash
# Sibling proof for ADR-0006: this package's wheel installs beside its siblings, the
# packages under the same provider namespace (xippios.usda.nass beside xippios.usda.psd),
# as portions of the PEP 420 namespaces between xippios and the package.
#
# sdk-template renders this file, and .github/workflows/siblings.yml that runs it, where
# the import path nests; copier update keeps both as the template's. The siblings are the
# repositories of the xippios organisation named sdk-<provider>-* whose distribution,
# xippios-<provider>-*, is on PyPI; uv installs the newest release of each that shares one
# xippios-core minor with this wheel, and a sibling with no such release is left out with a
# warning. The script builds the wheel, installs it with them into a
# fresh virtual environment, fails if a namespace level is a regular package (an
# __init__.py at xippios/ or xippios/<provider>/), imports every package under the
# provider namespace, checks that every tracked file of the package ships in the wheel and
# runs `uv pip check`. It calls nothing upstream. Needs the network, no key. Run from
# anywhere: .github/scripts/check-siblings.sh
#
#   XIPPIOS_SIBLINGS  one requirement per line, replacing the discovered siblings: a
#                     sibling not on PyPI yet, from its checkout in the workspace or from
#                     git; set and empty, the wheel is installed alone
#   GITHUB_TOKEN      where set, authenticates the listing of the organisation's
#                     repositories (siblings.yml passes the job's read-only token)
#   PYTHON            the environment's Python version, 3.12 unless set
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
unset VIRTUAL_ENV  # never install into whatever environment the shell has active
cd "$root"

# The distribution and the import path as copier recorded them (ADR-0006).
answer() { sed -n "s/^$1: //p" .copier-answers.yml; }
slug="$(answer source_slug)"
import_path="$(answer import_path)"
if [ -z "$slug" ] || [ -z "$import_path" ]; then
  echo "error: .copier-answers.yml names no source_slug or import_path" >&2
  exit 1
fi
distribution="xippios-$slug"
package="xippios.$import_path"
provider="${import_path%%.*}"

uv venv --quiet --python "${PYTHON:-3.12}" "$work/venv"
python="$work/venv/bin/python"

if [ -n "${XIPPIOS_SIBLINGS+set}" ]; then
  siblings="$XIPPIOS_SIBLINGS"
  echo "siblings from XIPPIOS_SIBLINGS"
else
  siblings="$("$python" - "$provider" "$distribution" <<'PY'
"""Print the siblings on PyPI: xippios-<provider>-* for each sdk-<provider>-* of xippios."""
import json
import os
import sys
import urllib.error
import urllib.request

provider, own = sys.argv[1:]
agent = {"User-Agent": "xippios check-siblings (+https://github.com/xippios)"}
headers = {**agent, "Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
repositories: list[str] = []
page = 1
while True:
    url = f"https://api.github.com/orgs/xippios/repos?type=public&per_page=100&page={page}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as got:
        listed = json.load(got)
    repositories += [repo["name"] for repo in listed if not repo["archived"]]
    if len(listed) < 100:
        break
    page += 1
for name in sorted(repositories):
    distribution = "xippios-" + name.removeprefix("sdk-")
    if not name.startswith(f"sdk-{provider}-") or distribution == own:
        continue
    simple = urllib.request.Request(f"https://pypi.org/simple/{distribution}/", headers=agent)
    try:
        urllib.request.urlopen(simple, timeout=30).close()
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        print(f"{distribution}: not on PyPI yet, left out", file=sys.stderr)
        continue
    print(distribution)
PY
)"
  echo "siblings on PyPI, from the repositories sdk-$provider-* of xippios"
fi
requirements=()
while IFS= read -r line; do
  if [ -n "$line" ]; then
    requirements+=("$line")
    echo "  $line"
  fi
done <<< "$siblings"
if [ "${#requirements[@]}" = 0 ]; then
  echo "  none: the wheel is installed alone"
fi

# A development pin of core (conventions §12): while pyproject.toml takes xippios-core from
# git, the wheel needs core from that pin too, which its bound alone would not fetch.
core="$("$python" - <<'PY'
import tomllib

with open("pyproject.toml", "rb") as file:
    pin = tomllib.load(file).get("tool", {}).get("uv", {}).get("sources", {}).get("xippios-core")
if isinstance(pin, dict) and "git" in pin:
    ref = next((pin[key] for key in ("rev", "tag", "branch") if key in pin), None)
    print(f"xippios-core @ git+{pin['git']}" + (f"@{ref}" if ref else ""))
PY
)"
if [ -n "$core" ]; then
  echo "xippios-core from the git pin in pyproject.toml: $core"
fi

uv build --quiet --wheel --out-dir "$work/dist"
wheel=("$work"/dist/*.whl)
# A sibling none of whose releases shares this wheel's xippios-core minor cannot install
# beside it until one of the two adopts the other's minor (conventions §15): it is left out
# with a warning, so the proof stays with the siblings on this wheel's minor. Any other
# conflict fails the check.
kept=()
for requirement in "${requirements[@]}"; do
  if trial="$(uv pip install --dry-run --python "$python" "${wheel[@]}" "$requirement" \
    ${core:+"$core"} 2>&1)"; then
    kept+=("$requirement")
  elif grep -q 'xippios-core' <<< "$trial"; then
    echo "::warning::${requirement}: no release shares this wheel's xippios-core minor; left out"
  else
    echo "$trial" >&2
    exit 1
  fi
done
uv pip install --python "$python" "${wheel[@]}" "${kept[@]}" ${core:+"$core"}

"$python" - "$package" <<'PY'
"""Every level above the package stays a namespace portion; every package under it imports."""
import importlib
import pkgutil
import sys
from importlib.metadata import version

package = sys.argv[1]
levels = package.split(".")
namespaces = [".".join(levels[:depth]) for depth in range(1, len(levels))]
for name in namespaces:
    module = importlib.import_module(name)
    if getattr(module, "__file__", None) is not None:
        sys.exit(f"error: {name} is a regular package ({module.__file__}), not a portion")
provider = sys.modules[namespaces[-1]]
found = pkgutil.iter_modules(provider.__path__, f"{provider.__name__}.")
names = sorted(info.name for info in found if info.ispkg)
if package not in names:
    sys.exit(f"error: {package} is not installed under {provider.__name__}")
for name in names:
    module = importlib.import_module(name)
    print(f"imported {name} {getattr(module, '__version__', '')}")
core = version("xippios-core")
print(f"ok: {' and '.join(namespaces)} stay namespace portions, on xippios-core {core}")
PY

site="$("$python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
missing=0
while IFS= read -r -d '' file; do
  if [ ! -e "$site/${file#src/}" ]; then
    echo "error: ${file#src/} is not in the wheel" >&2
    missing=1
  fi
done < <(git ls-files -z -- "src/${package//.//}")
if [ "$missing" != 0 ]; then
  exit 1
fi
echo "ok: every tracked file of src/${package//.//} ships in the wheel"
uv pip check --python "$python"
