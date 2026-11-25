- The generated `CLAUDE.md` keeps what the package wraps, its layout, its commands with the
  live run, how a template release reaches it and its specifics, and restates no rule that
  sdk-core's conventions hold: `## Code rules`, `## When something is unclear`, the offline
  paragraphs of `## Commands` and the two file lists of `## Template updates` leave it, the
  section naming `_skip_if_exists` of `copier.yml` in place of the lists. The nine rules of
  `## Never` move into `.claude/rules/never.md`, a file of the template's that every update
  writes again and that Claude Code loads at launch by its place, and the Layout moves into
  `docs/layout.md`, the source's own, which `CLAUDE.md` imports and which holds what the
  source adds to the family's tree, laid out once in this repository's README. The Never
  file's rule on credentials names the tenants' key pattern only where the tenants hold the
  key, since the template knows no variable of tenants that hold another credential.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/233,
  https://github.com/xippios/sdk-template/issues/301)
  - Hand-apply: `CLAUDE.md` — delete `## Code rules`, `## When something is unclear` and
    `## Never`, the paragraph after the code block of `## Commands` that says the tests run
    offline and, where the source has a key, the one after it on the key's placeholder, the
    Layout's code block with the paragraph below it and the two file lists of
    `## Template updates`, then write the intro, `## Layout` with its import line
    `@docs/layout.md` and `## Template updates` as a render of this release has them, and
    move each line of the source's own from what leaves into its
    `## <source name> specifics` and each entry of its Layout that this repository's README
    does not lay out, a module of `api/` or `parse/` or a script or test of its own, into
    `docs/layout.md`, which takes about 130 lines out of a render's file and about 1,680 out
    of the twelve sources' files together, an estimate. Then search what stays, and the
    lines moved into `docs/layout.md`, for each name below, which a render of v0.4.0 or
    v0.4.1, the template's proofs or a source's own tests held and which this release or
    core 0.5.0's family check takes out, and reword or delete each line that names one the
    source no longer holds: `organization.yml`, `xippios_placeholder_key_envs`, the answers
    `api_base_url`, `api_key_location`, `api_key_name`, `rate_limit_per_minute`,
    `rate_limit_burst`, `rate_limit_provenance`, `gateway`, `tenant_credential_env` and
    `human`, `INSTRUCTIONS` and `BOUND_INSTRUCTIONS` of `mcp.py`, `READERS` and `ALLOWED`
    of `tests/test_built_answers.py`, `test_upstream_answers` of `tests/test_live.py`,
    `LEVEL` of `ci.yml`, `tests/test_contract.py`, whose package contract core's family
    check holds, and the proof shapes `--gateway` and `--tenants-keyless`. The names that
    leave core stand in core's list, "The names that left" under "Adopting core 0.5.0" of
    sdk-core's `docs/handover.md` at its tag `v0.5.0`, and this note repeats none of them —
    sdk-core's conventions hold the rules, the template's Never file keeps the rules no
    change breaks in what Claude Code loads, a change that adds a module then updates a
    file of the source's own, and a line that names what left points its reader to nothing.
    `docs/layout.md` — fill it with what the package adds to the family's tree, which this
    repository's README lays out once, in a code block laid out as that tree is, a line per
    file or directory with what it holds, from the entries that the item above moves out of
    the Layout of `CLAUDE.md`, each module of `api/` or `parse/` and each script or test of
    the source's own among them — the update creates the file where the repository has
    none, holding the render's stub, which says what the file holds and that the change
    that adds a module updates it, and it is the source's from this release on, so no later
    update writes it again.
