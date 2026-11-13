- The generated `.claude/settings.json`, and this repository's own, allow the checks and
  local git and no longer allow a push, a pull request, a merge or the GitHub CLI's views,
  so Claude Code asks before each. Both deny what destroys work or reads a secret, as
  before, and this repository's own allows `scripts/prove.sh` beside them.
  (https://github.com/xippios/sdk-template/issues/127)
