- `copier.yml` asks `shape`, `source` by default, and `general` renders the general part of a
  repository alone, its CI, release train, changelog, decision records, organization's checks
  and `/release-prep` around a package with its version, for a package of the family that
  wraps no API: none of a source's other files and none of its seven questions of an
  upstream, a `repository_name` that defaults to `sdk-<slug>`, and a `pyproject.toml` that is
  the repository's once rendered. Where its package holds a key, which `api_key_env` names in
  this shape too, it renders `_client.py`, which declares the key in `ENV_VARS`, holds no
  client and is the package's to fill. A source's update records `shape: source` and changes
  no other file. (ADR-0003, https://github.com/xippios/sdk-template/issues/302,
  https://github.com/xippios/sdk-core/issues/538)
  - Hand-apply: `README.md` — nothing to port — a source renders it as before, and the
    general shape's lines matter to a new repository of that shape alone.
    `CLAUDE.md` — nothing to port — the same.
    `CHANGELOG.md` — nothing to port — the same.
    `docs/layout.md` — nothing to port — the same.
    `tests/conftest.py` — nothing to port — the same.
    `src/xippios/<import path>/__init__.py` — nothing to port — the same.
    `src/xippios/<import path>/_client.py` — nothing to port — the same.
