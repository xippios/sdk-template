- This repository's `CLAUDE.md` and the generated one say which commit subjects follow
  Conventional Commits: a pull request's own commits, not the commit that lands it on
  `main`, whose subject GitHub writes.
  (https://github.com/xippios/sdk-template/issues/149)
  - Hand-apply: `CLAUDE.md` — in Code rules, follow the sentence on Conventional Commits
    with the clause `template/CLAUDE.md.jinja` adds at this tag — the rule binds a pull
    request's own commits, and the commit that lands one takes the subject GitHub writes.
