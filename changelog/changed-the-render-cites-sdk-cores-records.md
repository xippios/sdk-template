- The generated `CLAUDE.md` and `README.md` cite sdk-core's decision records as
  `sdk-core ADR-NNNN`, where they gave a bare number, since a source cites its own records
  as `ADR-NNNN`, as its `docs/adr/README.md` says, and its first record would make a bare
  number ambiguous. (https://github.com/xippios/sdk-template/issues/152)
  - Hand-apply: `CLAUDE.md` — write each `ADR-NNNN` that cites a record of sdk-core as
    `sdk-core ADR-NNNN`, in the table, the layout, the text and the lists alike — a bare
    number is the source's own record.
    `README.md` — the same in the comment beside the line on the packages the source
    depends on, where it has one — a bare number is the source's own record.
