- The generated `CLAUDE.md`'s "Depends on" row says what each kind of dependency serves: a
  source package's task layer and its models, and a publisher's shared package's public
  names, since a shared package has no tasks. (sdk-core ADR-0021, sdk-core ADR-0065,
  https://github.com/xippios/sdk-template/issues/335)
  - Hand-apply: `CLAUDE.md` — sdk-usda-psd and sdk-usda-gats, which declare their dependency
    on the shared package `xippios-usda-fas` at their adoption of core 0.5.0, write the row
    as a render of this release has it, and sdk-usda-esr keeps the row it has worded — the
    update never writes a source's `CLAUDE.md`, and the row said that a dependency serves its
    task layer alone.
