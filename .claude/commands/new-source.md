Create a new xippios source repository: $ARGUMENTS

This runs `scripts/new-source.sh`, which generates `sdk-<slug>` from this template, runs
the full check suite on it, creates the GitHub repository with topics and the `pypi`
environment, and opens the scaffold PR. The script is the only thing that touches GitHub.

1. Read `copier.yml` for the questions. From the arguments and the conversation, collect
   an answer for each: `source_slug`, `source_name`, `upstream_url`, `upstream_docs_url`,
   `api_base_url`, `api_key_env` (empty if none) with `api_key_location` and
   `api_key_name`, `rate_limit_per_minute`, `rate_limit_burst`, `rate_limit_provenance`,
   `needs_write_tools`, `domain_topic`. Ask the user for anything you do not have. Never
   guess a URL or a rate limit: the pace, the burst and whether the pace is documented
   or self-imposed come from the upstream documentation the user points you at, or from
   the user (ADR-0010).
2. Leave `core_version` at its default, `0.2.0`, the current `xippios-core` release on
   PyPI, rendered `xippios-core~=0.2.0` (ADR-0018), unless the user names another. Leave
   `core_git_ref` out; pass `-d core_git_ref=main` only to build against unreleased core.
   Later core minors and template releases reach the repository through its adoption
   PRs, `chore/template-update-<tag>`, which its `/adopt-release` walks (conventions §15).
3. Run, with every answer as a `-d key=value` pair:

   ```bash
   scripts/new-source.sh <slug> -d "source_name=..." -d "upstream_url=..." ...
   ```

   Add `--local-only` only if the user asked for a dry run.
4. If a check fails on the generated repository, the template is at fault: fix it here,
   remove the generated directory, and run again. Do not patch the generated repo by hand.
5. Report the PR URL and repeat the three human steps the script prints: PyPI pending
   publisher; the API key (if the org secret named by `api_key_env` exists already, a
   key shared by several sources, ADR-0009, the new repository is added to that
   secret's repository access in the org settings, never with `gh secret set --repos`,
   which replaces the list; otherwise the key goes into `.envrc` and a new org secret;
   the nightly `live.yml` needs it either way); review and merge.

The script's `gh repo create` and `gh api -X PUT .../environments/pypi` will each raise a
permission prompt; that approval is the human gate. If the script stops because the org's
default branch is not `main`, that is an org setting only a human changes; report it and
stop. Never run those commands outside the
script, never run `gh secret`, never tag or merge.
