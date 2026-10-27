#!/usr/bin/env bash
# Prove the template: generate a throwaway sdk-example-api from the WORKING TREE and run
# the full check suite on it (uv sync, ruff, mypy, pytest with core's family check,
# pre-commit), then re-render enums.py from the (empty) packaged lists and require it
# unchanged, require the unfilled refresh_upstream.py skeleton to refuse to run, and run
# the sibling check on the nested render with the wheel alone (none renders where flat).
# No GitHub involved. The placeholder key is core's plugin's to guarantee, and its own
# suite tests it.
#
# usage: scripts/prove.sh [--dest DIR] [--core-ref REF] [--keyless] [--keep] [-d key=value ...]
#   --core-ref REF   sdk-core commit to depend on, main or a full SHA; default "" = the
#                    PyPI release, e.g. --core-ref main to prove against unreleased core
#   --keyless        a keyless flat source, sdk-example (xippios.example), instead of the
#                    keyed nested sdk-example-api (xippios.example.api)
#   --keep           leave the generated repository in place
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest=""
core_ref=""
keyless=0
keep=0
extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dest) dest="$2"; shift ;;
    --core-ref) core_ref="$2"; shift ;;
    --keyless) keyless=1 ;;
    --keep) keep=1 ;;
    -d) extra+=(-d "$2"); shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
# The keyed slug nests (example-api → xippios.example.api) so the proof covers ADR-0006;
# the keyless one stays flat, as a new keyless source such as eurostat starts.
if [ "$keyless" = 1 ]; then
  slug="example"
  key=()
else
  slug="example-api"
  key=(-d "api_key_env=EXAMPLE_API_KEY" -d "api_key_location=query")
fi
work="$(mktemp -d "${TMPDIR:-/tmp}/sdk-template-prove.XXXXXX")"
dest="${dest:-$work/sdk-$slug}"

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

# The evidence file and the topic go through the same path as in a real run: the PR body
# new-source.sh prints under --local-only lists them under Assumptions.
evidence="$work/evidence.md"
echo "- Every answer is the proof's own: api.example.org is no upstream." > "$evidence"
"$here/scripts/new-source.sh" "$slug" --local-only --topic example-domain \
  --evidence "$evidence" --dest "$dest" --template "$snapshot" \
  -d "source_name=Example Data Service" \
  -d "upstream_url=https://api.example.org" \
  -d "upstream_docs_url=https://api.example.org/docs" \
  -d "api_base_url=https://api.example.org/v1" \
  "${key[@]}" \
  -d "rate_limit_per_minute=120" \
  -d "core_git_ref=$core_ref" \
  "${extra[@]}" | tee "$work/new-source.log"

echo
echo "==> the printed PR body: Enforced by CI ticked, no Adoption PR block, the assumptions"
body="$(sed -n "/^==> the scaffold PR's body/,/^generated and verified/p" "$work/new-source.log")"
ci_block="$(awk '/^### Enforced by CI/ { on = 1; next } /^##/ { on = 0 } on' <<<"$body")"
fail() { echo "error: the printed PR body: $1" >&2; exit 1; }
grep -q '^- \[x\] ' <<<"$ci_block" || fail "no ticked item under Enforced by CI"
! grep -q '^- \[ \] ' <<<"$ci_block" || fail "an unticked item under Enforced by CI"
! grep -q '^### Adoption PR' <<<"$body" || fail "the Adoption PR block is kept"
grep -qxF -- "- The GitHub topic for the domain: \`example-domain\`." <<<"$body" \
  || fail "no topic under Assumptions"
grep -qxF -- "$(cat "$evidence")" <<<"$body" || fail "no evidence under Assumptions"
echo "$(grep -c '^- \[x\] ' <<<"$ci_block") items ticked, no Adoption PR block, topic and evidence listed"

echo
echo "==> refresh_reference.py --render-only renders the shipped enums.py unchanged"
(cd "$dest" && uv run python scripts/refresh_reference.py --render-only && git diff --exit-code)

echo
echo "==> refresh_upstream.py, the skeleton, refuses to run until a source fills it"
if (cd "$dest" && uv run python scripts/refresh_upstream.py --check) 2> "$work/refresh.err"; then
  echo "error: the unfilled skeleton ran" >&2
  exit 1
fi
refusal="$(grep "Nothing to fetch: fill PAGES" "$work/refresh.err")" \
  || { cat "$work/refresh.err" >&2; exit 1; }
echo "refused: $refusal"

echo
if [ "$keyless" = 1 ]; then
  echo "==> no sibling check where the import path is flat"
  if [ -e "$dest/.github/workflows/siblings.yml" ] || [ -e "$dest/.github/scripts" ]; then
    echo "error: a flat source renders the sibling check" >&2
    exit 1
  fi
  echo "neither .github/workflows/siblings.yml nor .github/scripts/ rendered"
else
  # XIPPIOS_SIBLINGS set and empty: the wheel alone, so the proof lists no repositories
  # on GitHub; the namespace levels, the import and the shipped files are checked as in CI.
  echo "==> .github/scripts/check-siblings.sh on the nested render, the wheel alone"
  (cd "$dest" && XIPPIOS_SIBLINGS= .github/scripts/check-siblings.sh)
fi

echo
echo "==> generated tree"
(cd "$dest" && git ls-files | sort)
if [ "$keep" = 1 ]; then
  echo "kept: $dest"
else
  rm -r "$work"
fi
