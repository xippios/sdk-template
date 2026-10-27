#!/usr/bin/env bash
# Create a new xippios-<source> repository from this template.
#
# usage: scripts/new-source.sh <source-slug> [options] [-d key=value ...]
#   -d key=value     answer to a question in copier.yml; unspecified questions take defaults
#   --topic DOMAIN   the GitHub topic for the domain (agriculture, trade-data, accounting),
#                    added beside xippios-sdk, python and mcp (conventions §13); required
#                    unless --local-only
#   --evidence FILE  markdown list items, one per answer that rests on upstream: the page that
#                    states it, a status-only probe of the host; the scaffold PR's body lists
#                    them under Assumptions after the answers
#   --local-only     generate and run the checks, do not touch GitHub; print the PR body instead
#   --dest DIR       where to generate (default: $XIPPIOS_SDK_ROOT or ~/github/sdk, then sdk-<slug>)
#   --template SRC   template source (default: the GitHub repository at its latest tag, so generated
#                    repos record a URL copier update can reach from any machine; a local path or
#                    snapshot works too and is what prove.sh passes)
#
# Everything that touches GitHub is at the end and runs only without --local-only. The
# scaffold PR's body is the generated PULL_REQUEST_TEMPLATE.md, filled from this run; the
# human steps that remain are in it and printed last. This script never tags or merges: a
# release PR's merge tags the release through the generated publish.yml (conventions §12).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
slug="${1:?usage: new-source.sh <source-slug> [--topic DOMAIN] [--local-only] [--dest DIR] [-d key=value ...]}"
shift
root="${XIPPIOS_SDK_ROOT:-$HOME/github/sdk}"
dest=""
template="https://github.com/xippios/sdk-template.git"
local_only=0
topic=""
evidence=""
data=()
while [ $# -gt 0 ]; do
  case "$1" in
    --topic) topic="$2"; shift ;;
    --evidence) evidence="$2"; shift ;;
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
# The domain topic is checked before anything is generated, so a missing or malformed one
# costs nothing: GitHub takes lowercase letters, digits and hyphens.
if [ -n "$topic" ] && ! [[ "$topic" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "error: --topic $topic: use lowercase letters, digits and single hyphens, e.g. trade-data" >&2
  exit 2
fi
if [ -z "$topic" ] && [ "$local_only" = 0 ]; then
  echo "error: --topic DOMAIN is required to create the repository (or pass --local-only)" >&2
  exit 2
fi
if [ -n "$evidence" ]; then
  if [ ! -f "$evidence" ]; then
    echo "error: --evidence $evidence: no such file" >&2
    exit 2
  fi
  evidence="$(cd "$(dirname "$evidence")" && pwd)/$(basename "$evidence")"
fi

answer() { grep -E "^$1:" "$dest/.copier-answers.yml" | sed -E "s/^$1: *//; s/^'(.*)'$/\1/; s/^\"(.*)\"$/\1/"; }

# The human steps that remain, numbered: printed last and written into the PR body.
human_steps() {
  cat <<MSG
1. PyPI: add a pending trusted publisher for xippios-$slug
   (owner xippios, repository sdk-$slug, workflow publish.yml, environment pypi);
   the first release's publish job needs it.
MSG
  if [ -n "$api_key_env" ]; then
    cat <<MSG
2. The key, $api_key_env. If the org secret $api_key_env exists already (one key
   shared by several sources, ADR-0009), add sdk-$slug to that secret's
   repository access in the org settings; never \`gh secret set --repos\`, which replaces
   the list. Otherwise put the key into ~/github/sdk/.envrc and create the org secret
   $api_key_env with access for sdk-$slug. Either way the nightly
   .github/workflows/live.yml needs it.
MSG
  else
    echo "2. No API key is needed for this source."
  fi
  cat <<MSG
3. Review the scaffold PR (read CLAUDE.md as a new engineer would) and merge it.
   Releases tag themselves: the merge of a release PR (/release-prep) runs publish.yml,
   which tags the version and waits for the approval of its pypi run.
MSG
  if [ "${team_found:-}" = 0 ]; then
    cat <<MSG
4. The team $team does not exist yet. Once it does, with the sessions' machine user
   among its members, give it write access to sdk-$slug.
MSG
  fi
}

# The scaffold PR's body ($1): the generated PULL_REQUEST_TEMPLATE.md with its summary (and
# the human steps) and its assumptions (the answers as .copier-answers.yml records them, the
# topic, the --evidence lines) filled in, the "Enforced by CI" block ticked, since the checks
# above passed, and the Adoption PR block deleted, as the template says for every PR but an
# adoption. The session completes the rest (/new-source). Written before anything is created
# on GitHub, so a template it cannot fill stops the script with nothing created.
write_body() {
  local summary assumptions
  summary="$(mktemp)"
  assumptions="$(mktemp)"
  {
    echo "Scaffold of \`xippios-$slug\` ($source_name), generated by \`scripts/new-source.sh\`"
    echo "from sdk-template \`$ref\`; it wraps no endpoint yet. Before this PR the script ran"
    echo "every check on the generated repository: \`ruff check\`, \`ruff format --check\`,"
    echo "\`mypy\`, \`pytest\` and \`pre-commit run --all-files\`."
    echo
    echo "Human steps that remain:"
    echo
    human_steps
  } > "$summary"
  {
    echo "- The answers, as \`.copier-answers.yml\` records them:"
    awk '/^#/ { next }
      /^[^ ]/ { if (item != "") print "  - `" item "`"; item = ($0 ~ /^_/) ? "" : $0; next }
      item != "" { sub(/^ +/, ""); item = item " " $0 }
      END { if (item != "") print "  - `" item "`" }' .copier-answers.yml
    if [ -n "$topic" ]; then
      echo "- The GitHub topic for the domain: \`$topic\`."
    else
      echo "- The GitHub topic for the domain: none given (\`--topic\`)."
    fi
    if [ -n "$evidence" ]; then
      cat "$evidence"
    else
      echo "- Evidence for the answers: none given (\`--evidence\`)."
    fi
  } > "$assumptions"
  awk -v summary="$summary" -v assumptions="$assumptions" '
    function emit(file,   line) { while ((getline line < file) > 0) print line; close(file) }
    /^##+ / { block = $0 }
    block ~ /^### Adoption PR/ { next }
    block == "## Summary" && /^<!--/ { emit(summary); filled++; next }
    block == "## Assumptions" && /^<!--/ { emit(assumptions); filled++; next }
    block == "### Enforced by CI" { sub(/^- \[ \] /, "- [x] ") }
    { print }
    END { if (filled != 2) exit 1 }' .github/PULL_REQUEST_TEMPLATE.md > "$1"
  rm -f "$summary" "$assumptions"
}

# The workspace's guard refuses work in a directory no session owns: a new source's
# directory is in a session's list under [sessions] in coordination/owners.toml before it
# is generated there. Johannes adds it; this only reminds.
owners="$root/coordination/owners.toml"
if [ "$(dirname "$dest")" = "$root" ] && [ -f "$owners" ] && ! grep -q "\"sdk-$slug\"" "$owners"; then
  echo "notice: no session owns sdk-$slug in $owners ([sessions]); the guard refuses work in" >&2
  echo "        $dest until Johannes adds it there" >&2
fi

if [ -d "$template" ]; then
  ref="$(git -C "$template" describe --tags --abbrev=0 2>/dev/null || echo HEAD)"
else
  ref="$(git ls-remote --tags --refs "$template" 2>/dev/null | sed 's#.*/##' | sort -V | tail -1)"
  ref="${ref:-HEAD}"
fi
echo "==> generating $dest from template ref $ref"
uv run --project "$here" copier copy --defaults --vcs-ref "$ref" -d "source_slug=$slug" "${data[@]}" "$template" "$dest"
cd "$dest"
source_name="$(answer source_name)"
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

body="$(mktemp)"
trap 'rm -f "$body"' EXIT
if [ "$local_only" = 1 ]; then
  write_body "$body"
  echo
  echo "==> the scaffold PR's body (no PR opened: --local-only)"
  cat "$body"
  echo
  echo "generated and verified: $dest (no GitHub repository created)"
  exit 0
fi

echo "==> GitHub repository $repo"
# Pre-flight, before anything is created: the family and the sdk-main-protection ruleset
# need the first branch to be main. The ruleset enforces its ci check on branch creation,
# so main cannot be created afterwards by rename or push; only the org setting can fix it.
org_default="$(gh api orgs/xippios --jq .default_repository_branch)"
if [ "$org_default" != "main" ]; then
  cat >&2 <<MSG
error: the organisation's default branch is '$org_default', not 'main'.
A new repository would start on '$org_default', and the sdk-main-protection ruleset blocks
creating 'main' later. An org admin sets Settings → Repository defaults → default branch
to 'main', then re-run this command. Nothing was created; $dest is generated and verified.
MSG
  exit 1
fi
# The sessions' team gets write access: sessions are to work on GitHub as a machine user
# that is a member of it. The team is read here, before anything is created. Until it
# exists (the machine user and its team are set up later), its 404 is a notice and the
# script goes on; any other error stops it with nothing created.
team="sdk-sessions"
team_found=0
if team_reply="$(gh api "orgs/xippios/teams/$team" 2>&1)"; then
  team_found=1
elif grep -q 'HTTP 404' <<<"$team_reply"; then
  echo "notice: the team $team does not exist yet, so $repo is added to no team; give the"
  echo "        team write access to it once the team exists"
else
  cat >&2 <<MSG
error: cannot read the team $team: $team_reply
Nothing was created; $dest is generated and verified.
MSG
  exit 1
fi
write_body "$body"
gh repo create "$repo" --public --license Apache-2.0 --description "xippios SDK for $source_name"
gh repo edit "$repo" --add-topic xippios-sdk --add-topic python --add-topic mcp --add-topic "$topic"
# Adoption and release PRs of merge class `auto` auto-merge after the reviewer's `ready`
# (ADR-0018, amendment (e)); merged branches are deleted, as in every sdk-* repository.
gh repo edit "$repo" --enable-auto-merge --delete-branch-on-merge
if [ "$team_found" = 1 ]; then
  gh api -X PUT "orgs/xippios/teams/$team/repos/$repo" -f permission=push --silent
fi
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
gh pr create --title "chore: scaffold xippios-$slug from sdk-template" --body-file "$body"

echo
echo "Done. Human steps that remain (also in the PR's body):"
human_steps | sed 's/^/  /'
cat <<MSG
Owners: sdk-$slug belongs to a session under [sessions] in coordination/owners.toml (Johannes
adds it), since the workspace's guard refuses work in a directory no session owns.
MSG
