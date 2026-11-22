- A multi-tenant source without a key names its live secrets after the reserved tenant's
  credential under `xippios_placeholder_key_envs` in `pyproject.toml`, since its own auth
  reads them, so core's plugin sets each in every test not marked live. A comment under
  `[project.scripts]` says that a script of the package's own goes after the servers' entry
  points, where an update keeps it while the template's lines beside it stay. Neither adds
  a question or a hidden answer, and sdk-google-mail, which wrote both by hand, keeps its
  script and list at its adoption and takes the render's comment above the list where its
  own wording conflicts. (https://github.com/xippios/sdk-template/issues/241)
