#!/usr/bin/env bash
# Prove the template: generate a throwaway sdk-example from the WORKING TREE and run the
# full check suite on it (uv sync, ruff, mypy, pytest, pre-commit), then pytest once more
# with the key variable set to a dummy value (keyed sources only). No GitHub involved.
#
# usage: scripts/prove.sh [--dest DIR] [--core-ref REF] [--keep] [-d key=value ...]
#   --core-ref REF   git ref of sdk-core to depend on; default "" = the PyPI release,
#                    e.g. --core-ref main to prove against unreleased core
#   --keep           leave the generated repository in place
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest=""
core_ref=""
keep=0
extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dest) dest="$2"; shift ;;
    --core-ref) core_ref="$2"; shift ;;
    --keep) keep=1 ;;
    -d) extra+=(-d "$2"); shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
work="$(mktemp -d "${TMPDIR:-/tmp}/sdk-template-prove.XXXXXX")"
dest="${dest:-$work/sdk-example-api}"

# Snapshot the working tree so uncommitted template changes are what gets proven.
snapshot="$work/template-src"
mkdir -p "$snapshot"
cp -r "$here/copier.yml" "$here/template" "$snapshot/"

# The slug nests (example-api → xippios.example.api) so the proof covers ADR-0006.
"$here/scripts/new-source.sh" example-api --local-only --dest "$dest" --template "$snapshot" \
  -d "source_name=Example Data Service" \
  -d "upstream_url=https://api.example.org" \
  -d "upstream_docs_url=https://api.example.org/docs" \
  -d "api_base_url=https://api.example.org/v1" \
  -d "api_key_env=EXAMPLE_API_KEY" \
  -d "api_key_location=query" \
  -d "rate_limit_per_minute=120" \
  -d "domain_topic=example-domain" \
  -d "core_git_ref=$core_ref" \
  "${extra[@]}"

# With a key variable set in the shell, as direnv does, every test that is not live must
# still send the placeholder: run the suite once more with a dummy value in the variable.
key_env="$(sed -nE "s/^api_key_env: *['\"]?([A-Z0-9_]*)['\"]?$/\1/p" "$dest/.copier-answers.yml")"
if [ -n "$key_env" ]; then
  echo
  echo "==> pytest with $key_env set to a dummy value"
  (cd "$dest" && env "$key_env=dummy-value-not-a-key" uv run pytest -q)
fi

echo
echo "==> generated tree"
(cd "$dest" && git ls-files | sort)
if [ "$keep" = 1 ]; then
  echo "kept: $dest"
else
  rm -r "$work"
fi
