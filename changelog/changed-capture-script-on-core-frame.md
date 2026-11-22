- A render's `scripts/refresh_upstream.py` declares the source's `Snapshot` as `SNAPSHOT`,
  which the frame of xippios-core 0.4.1, `xippios.core.refresh`, fetches, checks and writes
  into `docs/upstream/`, in place of the template's skeleton of the whole capture. The
  rendered `/refresh-upstream` and `CLAUDE.md` say what a source fills in the declaration,
  and the converter its `reduce` uses is pinned in the dev group of `pyproject.toml` alone,
  since the script runs in the project's environment with no `# /// script` block. An
  adoption deletes its port of the skeleton and declares its pages, attribution and hooks
  on core's frame, whose `FETCHED.md` holds the table `Not fetched` and the row of
  `OBSERVED.md`, so it needs no decision of its own for either.
  (https://github.com/xippios/sdk-template/issues/235, https://github.com/xippios/sdk-template/issues/240, https://github.com/xippios/sdk-core/issues/363)
  - Hand-apply: `scripts/refresh_upstream.py` — delete the port of the 0.4.0 skeleton, its
    `# /// script` block among it, and declare the source's `Snapshot` as `SNAPSHOT` with
    its pages, attribution, pages left out, vocabulary, capture and hooks, run by
    `run(SNAPSHOT)` under `if __name__ == "__main__":` alone, as the source's part of
    "Adopting core 0.4.1" in sdk-core's `docs/handover.md` lists it — core's frame writes
    the table `Not fetched` and the row of `OBSERVED.md` from the first refresh on, so a
    source's row for the table closes with its patch.
    `CLAUDE.md` — write the Layout's line of `scripts/refresh_upstream.py` as the render
    has it — the line calls the source's filled script the template's skeleton.
