- The README says what a source checks on its `main` before it takes a release. Its own
  lines in the template's files show as the diff of `copier recopy --defaults --overwrite
  --vcs-ref=:current:` in a clean checkout, and the update carries them on, silently where
  the release leaves their place alone. Its recorded answers, `has_files` among them, stay
  as they are at the update, a wrong one included, and a wrong one changes in a pull
  request of its own with `copier update --defaults --vcs-ref=:current: -d
  <answer>=<value>`, the files the source fills taking the answer's lines by hand there.
  (https://github.com/xippios/sdk-template/issues/152,
  https://github.com/xippios/sdk-eurostat/issues/21)
