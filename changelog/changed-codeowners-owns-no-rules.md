- The generated `.github/CODEOWNERS` no longer owns `/rules/**`, a path no source has, and
  its header and the `human` answer's help name the five paths it owns. `copier update`
  brings it, so nothing is applied by hand.
  (https://github.com/xippios/sdk-template/issues/152)
