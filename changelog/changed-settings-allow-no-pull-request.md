- The generated `.claude/settings.json` allows the checks and local git and no longer
  allows a push, a pull request, a merge or the GitHub CLI's views, so Claude Code asks
  before each. This repository's own file takes the same rules and drops its deny of
  `gh pr merge`, which is asked from now on, so both deny the same, what destroys work or
  reads a secret, and it allows `scripts/prove.sh` beside them.
  (https://github.com/xippios/sdk-template/issues/127)
