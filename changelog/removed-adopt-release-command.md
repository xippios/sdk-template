- A generated repository no longer has `/adopt-release`: `copier update` deletes its copy.
  A template release is taken with `uvx --from 'copier>=9.19' copier update --defaults
  --vcs-ref=<tag>` in a pull request of its own, as the generated `/release-prep` says, and
  this `CHANGELOG.md` says what each release asks to be applied by hand.
  (https://github.com/xippios/sdk-template/issues/120)
  - Hand-apply: `CLAUDE.md` — drop `adopt-release` from the layout's `.claude/commands/`
    line — the update deletes the command.
