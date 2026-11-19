- `/record-fixture` says that a pull request that renames or moves a fixture moves its
  audited entries in `.secrets.baseline` to the new path in the same commit, their
  `"is_secret": false` kept. The baseline keys each entry by the file's path, so the hook
  flags the lines again under the new path, and a rescan keeps them there with the audit
  dropped. `copier update` brings the command.
  (https://github.com/xippios/sdk-template/issues/42)
