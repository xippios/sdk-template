- `/release-prep`'s SemVer check says that a source's adoption of a core minor takes a
  minor of the source, whatever else its release brings, since it moves the core bound to
  the new minor, as sdk-core's conventions §12 sets from core 0.4.0. Added tasks or
  parameters make a patch. `copier update` brings the command.
  (ADR-0039, https://github.com/xippios/sdk-template/issues/169)
