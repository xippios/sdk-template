- The generated `.pre-commit-config.yaml` takes sdk-core's rule that the secret scan skips
  the line on which core's recorder writes a cut body's `sha256`, 64 hex digits, so a cut
  fixture adds no audited entry to `.secrets.baseline`. At the adoption, the hook's first
  run over a fixture whose `sha256` line has an audited entry drops that entry, rewrites
  the baseline and fails once, until the rewritten file is added. A body stored base64 and
  upstream's own identifiers in a snapshot are scanned as before and keep their entries.
  (https://github.com/xippios/sdk-template/issues/42)
