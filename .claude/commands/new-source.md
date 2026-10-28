Create a new xippios source repository: $ARGUMENTS

This runs `scripts/new-source.sh`, which generates `sdk-<slug>` from this template, runs
the full check suite on it, creates the GitHub repository with topics, auto-merge,
branch deletion on merge, the `sdk-sessions` team where it exists and the `pypi`
environment, and opens the scaffold PR. The script is the only thing that touches GitHub.
Before it runs, `sdk-<slug>` belongs to a session under `[sessions]` in
`coordination/owners.toml` of the family workspace, which Johannes edits: the workspace's
guard refuses work in a directory no session owns. If it does not, stop and ask for it.

1. Read `copier.yml` for the questions. From the arguments and the conversation, collect
   an answer for each: `source_slug`, `source_name`, `upstream_url`, `upstream_docs_url`,
   `api_base_url`, `gateway` (`api.data.gov` for an API that gateway fronts, which
   derives the three key answers, so pass none of them; else leave it out, `none`),
   `api_key_env` (empty if none) with `api_key_location` and `api_key_name`,
   `rate_limit_per_minute`, `rate_limit_burst`, `rate_limit_provenance`,
   and the GitHub topic for the domain (`agriculture`, `trade-data`, `accounting`), which
   is no answer but the script's `--topic` (conventions §13). Ask the user for anything
   you do not have. Never guess a URL or a rate limit: the pace, the burst and whether
   the pace is documented or self-imposed come from the upstream documentation the user
   points you at, or from the user (ADR-0010).
2. Leave `core_version` at its default, `0.3.0`, the `xippios-core` release the template
   adopts, rendered `xippios-core~=0.3.0` (ADR-0018, amendment c), unless the user names
   another. Leave `core_git_ref` out; pass
   `-d core_git_ref=<sha>`, the full 40-character SHA of a commit on sdk-core's `main`, or
   `-d core_git_ref=main`, only to build against unreleased core.
   Later core minors and template releases reach the repository through its adoption
   PRs, `chore/template-update-<tag>`, which its `/adopt-release` walks (conventions §15).
3. Write the evidence for the answers to a file outside the repository, as markdown list
   items, one per answer that rests on upstream: the page and section that states the
   base URL, the key and the pace, or the user's word; the status a status-only probe of
   the host returned. Run, with the topic, the evidence and every answer as a
   `-d key=value` pair:

   ```bash
   scripts/new-source.sh <slug> --topic <domain> --evidence <file> -d "source_name=..." ...
   ```

   Add `--local-only` only if the user asked for a dry run; it prints the PR body instead.
4. If a check fails on the generated repository, the template is at fault: fix it here,
   remove the generated directory, and run again. Do not patch the generated repo by hand.
5. The script opens the scaffold PR with its body filled from the generated
   `.github/PULL_REQUEST_TEMPLATE.md`: the summary with the human steps, the answers, the
   topic and your evidence under Assumptions, the "Enforced by CI" block ticked (its
   checks passed before the PR) and the Adoption PR block deleted. Complete it with
   `gh pr edit <number> --body-file <file>`, as the definition of done says: tick each
   other item or give it a one-line reason (a scaffold adds no task, endpoint or fixture),
   and fill the open questions and the decisions taken.
6. Report the PR URL and repeat the three human steps the script prints: PyPI pending
   publisher, which the first release's publish job needs; the API key (if the org
   secret named by `api_key_env` exists already, a key shared by several sources,
   ADR-0009, the new repository is added to that secret's repository access in the org
   settings, never with `gh secret set --repos`, which replaces the list; otherwise the
   key goes into `.envrc` and a new org secret; the nightly `live.yml` needs it either
   way); the review and merge of the scaffold PR. Releases tag themselves: a release
   PR's merge runs `publish.yml`, which tags the version and waits for the approval of
   its `pypi` run. Repeat any step or notice the script printed beyond them (the team,
   the owners entry).

The script's `gh repo create` and `gh api -X PUT .../environments/pypi` will each raise a
permission prompt; that approval is the human gate. If the script stops because the org's
default branch is not `main`, that is an org setting only a human changes; report it and
stop. Never run those commands outside the
script, never run `gh secret`, never tag or merge.
