- The template's own `pyproject.toml` names the template's latest release, where it said
  0.1.0, and each release's pull request sets it with the heading it writes into
  `CHANGELOG.md`. A test holds the two equal, and the template's CI syncs with
  `uv sync --locked`, which fails on a `uv.lock` the manifest has left behind. A generated
  repository is unchanged. (https://github.com/xippios/sdk-template/issues/101)
