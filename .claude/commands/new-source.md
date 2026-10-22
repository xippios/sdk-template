Create a new xippios source repository: $ARGUMENTS

This runs `scripts/new-source.sh`, which generates `sdk-<slug>` from this template, runs
the full check suite on it, creates the GitHub repository with topics and the `pypi`
environment, and opens the scaffold PR. The script is the only thing that touches GitHub.

1. Read `copier.yml` for the questions. From the arguments and the conversation, collect
   an answer for each: `source_slug`, `source_name`, `upstream_url`, `upstream_docs_url`,
   `api_base_url`, `api_key_env` (empty if none) with `api_key_location` and
   `api_key_name`, `rate_limit_per_minute`, `needs_write_tools`, `domain_topic`. Ask the
   user for anything you do not have. Never guess a URL or a rate limit; both come from
   the upstream documentation the user points you at.
2. Leave `core_git_ref` out: `xippios-core` is on PyPI. Pass `-d core_git_ref=main` only
   to build against unreleased core.
3. Run, with every answer as a `-d key=value` pair:

   ```bash
   scripts/new-source.sh <slug> -d "source_name=..." -d "upstream_url=..." ...
   ```

   Add `--local-only` only if the user asked for a dry run.
4. If a check fails on the generated repository, the template is at fault: fix it here,
   remove the generated directory, and run again. Do not patch the generated repo by hand.
5. Report the PR URL and repeat the three human steps the script prints: PyPI pending
   publisher, API key into `.envrc` and as an org secret, review and merge.

The script's `gh repo create` and `gh api -X PUT .../environments/pypi` will each raise a
permission prompt; that approval is the human gate. If the script stops because the org's
default branch is not `main`, that is an org setting only a human changes; report it and
stop. Never run those commands outside the
script, never run `gh secret`, never tag or merge.
