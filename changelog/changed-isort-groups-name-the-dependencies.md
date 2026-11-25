- The rendered `pyproject.toml` names the import path of each package of
  `source_dependencies` beside `xippios.core` in ruff's `known-third-party`, the slug with
  dots as `import_path`'s default, so a dependency's imports sort with core's by the
  template's line. In the general shape, whose `pyproject.toml` is the repository's, the line
  comes at the first render. A source that added the line by hand takes it from the update,
  which renders it the same. (https://github.com/xippios/sdk-template/issues/317)
