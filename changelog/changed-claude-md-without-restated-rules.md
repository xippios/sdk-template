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
  key, since the template knows no variable of tenants that hold another credential. A
  render's `CLAUDE.md` holds 74 or 75 lines where it held 204 to 210.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/233,
  https://github.com/xippios/sdk-template/issues/301)
  - Hand-apply: `CLAUDE.md` — delete `## Code rules`, `## When something is unclear` and
    `## Never`, the two paragraphs after the code block of `## Commands` that say the tests
    run offline and send the key's placeholder, the Layout's code block with the paragraph
    below it and the two file lists of `## Template updates`, then write the intro,
    `## Layout` with its import line `@docs/layout.md` and `## Template updates` as a render
    of this release has them, and move each line of the source's own from what leaves into
    its `## <source name> specifics` and each entry of its Layout that this repository's
    README does not lay out, a module of `api/` or `parse/` or a script or test of its own,
    into `docs/layout.md`, which takes about 130 lines out of a render's file and about
    1,680 out of the twelve sources' files together, an estimate — sdk-core's conventions
    hold the rules, the template's Never file keeps the rules no change breaks in what
    Claude Code loads, and a change that adds a module then updates a file of the source's
    own.
    `docs/layout.md` — nothing to port, since the update creates it where the repository
    has none and the hand edit of `CLAUDE.md` above fills it — it is the source's from this
    release on, so no later update writes it again.
