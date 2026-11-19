- `/record-fixture` says that a pull request that renames or moves a fixture moves its
  audited entries in `.secrets.baseline` to the new path in the same commit, their
  `"is_secret": false` kept. Both the key under `results` and each entry's `"filename"`
  take the new path, and the baseline is staged with the move, since the hook flags the
  lines again while either names the old path or the baseline's change is unstaged. A
  rescan keeps them under the new path with the audit dropped. `copier update` brings the
  command.
  (https://github.com/xippios/sdk-template/issues/42)
