- The generated `/release-prep` assembles the release's section from the fragments under
  `changelog/` and what `## [Unreleased]` holds, by hand as `changelog/README.md` lays it
  out, and deletes the fragments. It keeps the source's own checks before a release, among
  them the refresh that gets no pull request while its records stay unchanged, a green live
  run over the release's base and the pending publisher's project name, and says nothing on
  how the pull request is opened or merged.
  (https://github.com/xippios/sdk-template/issues/130,
  https://github.com/xippios/sdk-template/issues/127)
