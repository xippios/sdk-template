- The generated samples table, `tests/fixtures/files/README.md` where `has_files` is true,
  ends in the column `Kept`, which says what of the file each sample keeps, as point d of
  sdk-core's amendment of 2026-11-18 to the record asks. The scaffold's text above it names
  the sample a script writes from one download where the file is over the 256 KiB cap and
  its format cannot be cut by bytes, a text that matters to new repositories only.
  (ADR-0020, https://github.com/xippios/sdk-template/issues/168)
  - Hand-apply: `tests/fixtures/files/README.md` — add the column `Kept` after `Fetched`,
    each row saying what of the file its sample keeps, such as the whole file or its first
    rows, where the table has no column that says so under a name of its own, as `Kept` or
    `What` — conventions §10 asks each sample's row to say what the sample keeps.
