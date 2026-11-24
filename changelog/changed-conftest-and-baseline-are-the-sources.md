- `tests/conftest.py` and `.secrets.baseline` are the source's from this release on: they
  stand under `_skip_if_exists`, so an update merges no line of the template's into a
  source's own there, and a later change of core's baseline or of the plugin's line reaches a
  source by a Hand-apply note. The render's README names neither `published_at` nor `vintage`
  among what every response carries and says under `## Workflows`, for each workflow the
  render holds, what it checks, when it runs, what the calling file hands over and what
  switches it, and a keyless `_client.py` declares no `API_KEY_ENV`. For new repositories
  only, the stub of `docs/upstream/FETCHED.md` keeps its title and one paragraph, since core's
  frame writes the file whole at the first refresh, and `scripts/refresh_upstream.py`
  declares no `reduce` of its own, so core's default keeps each page as fetched.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/308)
  - Hand-apply: `README.md` — in the first paragraph, say that every response carries its
    metadata (source, endpoint, retrieved_at, request), naming `published_at` and `vintage`
    only where every task sets them, and add `## Workflows` before `## Documents` as a render
    of this release holds it with the source's answers, one paragraph for each file under
    `.github/workflows/` — core's `Meta` leaves both fields to the task that knows them, and
    the organization's rule has the README say what each workflow does, since the workflow
    files carry no comment.
    `src/xippios/<import path>/_client.py` — in sdk-eurostat, sdk-faostat, sdk-google-mail,
    sdk-usda-esmis and sdk-usda-wasde, delete the line `API_KEY_ENV: str | None = None` and
    the name `"API_KEY_ENV"` in `__all__` — a source without a key declares no key's
    variable, and `ENV_VARS` names what a host sets.
    `src/xippios/<import path>/errors.py` — delete it where it still holds the scaffold's
    `__all__: list[str] = []` and no class — a stub that the source never filled says
    nothing, and an update leaves it deleted.
    `src/xippios/<import path>/enums.py` — delete it where it still holds the scaffold's
    `__all__ = []` and no enum — the same.
    `tests/conftest.py` — nothing to port: the file is the source's from this release on —
    an update no longer merges the template's lines into it.
    `.secrets.baseline` — nothing to port: the file is the source's from this release on —
    an update no longer merges the template's lines into the entries the source audited.
