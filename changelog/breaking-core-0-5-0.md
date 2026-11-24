- A render depends on xippios-core 0.5.0, `core_version`'s default, by the bound
  `xippios-core~=0.5.0`, its extras likewise, and the six files it copies from sdk-core,
  `ci.yml`, `publish.yml`, `.pre-commit-config.yaml`, `.secrets.baseline`, `.python-version`
  and `LICENSE`, follow core's bytes at 0.5.0. `ci.yml` and `publish.yml` carry no comment
  but the version after a pinned action, the template's own lines among them, as core's
  bytes carry none (conventions §13), and the render's `pyproject.toml` names no
  `xippios_placeholder_key_envs`, since core's plugin sets each secret variable of the
  package's `ENV_VARS` in `_client.py` to its placeholder. A source takes them by its
  adoption, whose update passes `-d core_version=0.5.0`.
  (https://github.com/xippios/sdk-template/issues/312, https://github.com/xippios/sdk-core/issues/475,
  https://github.com/xippios/sdk-core/issues/505)
  - Hand-apply: `pyproject.toml` — in sdk-faostat, delete the line
    `xippios_placeholder_key_envs = [...]` that it wrote by hand under
    `[tool.pytest.ini_options]`, with its comment, which the update keeps as the source's
    own line — core's plugin reads `ENV_VARS`, which declares both variables, and no longer
    reads the option.
    `README.md` — in the paragraph on `publish.yml` under `## Workflows`, say that its job
    `tag` holds the one checkout of the repository that keeps its credentials, since it
    pushes the tag with the job's token, and that every other checkout sets
    `persist-credentials: false` — conventions §13 has the README name that exception, which
    the workflow's comment named before.
    `tests/conftest.py` — where its comment says that a key's variable is named under
    `xippios_placeholder_key_envs` in `pyproject.toml`, say that core's plugin reads it from
    `ENV_VARS` in `_client.py` — the option leaves core.
