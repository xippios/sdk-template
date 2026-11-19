- `/record-fixture` says that a fixture over the 256 KiB cap that a pull request only moves
  stays as it was recorded, and that the pull request that records it again cuts it: no
  fixture is kept whole over the cap by exception, and the cap step of `ci.yml` keeps no
  list of them. `copier update` brings the command.
  (ADR-0040, https://github.com/xippios/sdk-template/issues/176)
