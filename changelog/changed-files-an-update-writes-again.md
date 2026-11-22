- The generated `CLAUDE.md` names, beside the files a source fills, the files that
  `copier update` writes again, `mcp.py` among them, so that a source keeps no text of its
  own in them. Its code rule on the three layers lets the tasks call reference data only
  where `has_reference_data` is `true`. A test holds the list equal to every rendered file
  outside `_skip_if_exists`, by path, so a file the template adds or renames outside
  `.github/` and `.claude/` is named in the same change.
  (https://github.com/xippios/sdk-template/issues/243, https://github.com/xippios/sdk-template/issues/244)
  - Hand-apply: `CLAUDE.md` — in `## Template updates`, follow the paragraph on the files
    the package fills with the paragraph on the files the update writes again, as a render
    with the package's answers has it, and where `has_reference_data` is `false`, as in
    sdk-x and sdk-google-mail, end the three-layer rule's clause at "the tasks call only
    wrappers" — `mcp.py` and the other files named there are written again at every
    update, and a source without reference data has none for its tasks to call.
