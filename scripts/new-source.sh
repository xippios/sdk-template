#!/usr/bin/env bash
# Create a new xippios-<source> repository from this template.
#
# usage: scripts/new-source.sh <source-slug> [options] [-d key=value ...]
#   -d key=value     answer to a question in copier.yml; unspecified questions take defaults
#   --local-only     generate and run the checks, do not touch GitHub
#   --dest DIR       where to generate (default: $XIPPIOS_SDK_ROOT or ~/github/sdk, then sdk-<slug>)
#   --template SRC   template source (default: this repository at its latest tag, or HEAD when untagged)
#
# Everything that touches GitHub is at the end and runs only without --local-only.
# Human steps that remain are printed last. This script never tags or merges.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
slug="${1:?usage: new-source.sh <source-slug> [--local-only] [--dest DIR] [-d key=value ...]}"
shift
root="${XIPPIOS_SDK_ROOT:-$HOME/github/sdk}"
dest=""
template="$here"
local_only=0
data=()
while [ $# -gt 0 ]; do
  case "$1" in
    --local-only) local_only=1 ;;
    --dest) dest="$2"; shift ;;
    --template) template="$2"; shift ;;
    -d) data+=(-d "$2"); shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
dest="${dest:-$root/sdk-$slug}"
repo="xippios/sdk-$slug"
if [ -e "$dest" ]; then
  echo "error: $dest already exists" >&2
  exit 1
fi

answer() { grep -E "^$1:" "$dest/.copier-answers.yml" | sed -E "s/^$1: *//; s/^'(.*)'$/\1/; s/^\"(.*)\"$/\1/"; }

ref="$(git -C "$template" describe --tags --abbrev=0 2>/dev/null || echo HEAD)"
echo "==> generating $dest from template ref $ref"
uv run --project "$here" copier copy --defaults --vcs-ref "$ref" -d "source_slug=$slug" "${data[@]}" "$template" "$dest"
cd "$dest"
source_name="$(answer source_name)"
domain_topic="$(answer domain_topic)"
api_key_env="$(answer api_key_env)"

echo "==> environment"
uv sync --all-extras

echo "==> checks"
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
git init -q -b main
git add -A
uv run pre-commit run --all-files

if [ "$local_only" = 1 ]; then
  echo
  echo "generated and verified: $dest (no GitHub repository created)"
  exit 0
fi

echo "==> GitHub repository $repo"
gh repo create "$repo" --public --license Apache-2.0 --description "xippios SDK for $source_name"
gh repo edit "$repo" --add-topic xippios-sdk --add-topic python --add-topic mcp --add-topic "$domain_topic"
reviewer="${XIPPIOS_PYPI_REVIEWER:-jdidaskalu}"
reviewer_id="$(gh api "users/$reviewer" --jq .id)"
printf '{"reviewers":[{"type":"User","id":%s}]}' "$reviewer_id" \
  | gh api -X PUT "repos/$repo/environments/pypi" --input - > /dev/null
git remote add origin "https://github.com/$repo.git"
git fetch -q origin
git reset -q                           # unstage; the generated files stay in the tree
rm -f LICENSE                          # origin/main carries the one GitHub generated
git checkout -q -B main origin/main    # local main = GitHub's initial commit
git switch -q -c feature/scaffold
git add -A
git commit -q -m "chore: scaffold xippios-$slug from sdk-template"
git push -q -u origin feature/scaffold
gh pr create --title "feat: scaffold xippios-$slug from sdk-template" \
  --body-file .github/PULL_REQUEST_TEMPLATE.md

cat <<MSG

Done. Human steps that remain:
  1. PyPI: add a pending trusted publisher for xippios-$slug
     (owner xippios, repository sdk-$slug, workflow publish.yml, environment pypi).
MSG
if [ -n "$api_key_env" ]; then
  echo "  2. Put $api_key_env into ~/github/sdk/.envrc and set it as an org secret (gh secret set, by a human)."
else
  echo "  2. No API key is needed for this source."
fi
echo "  3. Review the PR (read CLAUDE.md as a new engineer would), merge, tag v0.1.0."
