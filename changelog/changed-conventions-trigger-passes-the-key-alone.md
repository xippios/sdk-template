- The rendered `conventions.yml` passes its two jobs the secret `ANTHROPIC_API_KEY` alone,
  with no line of a read token, as the README of xippios/.github has a repository that
  reads no private document take the file. The shared workflows take the read token as
  optional, so `conventions / conventions` and `range / range` run as before, and this
  repository's own copy, byte for byte the render's, changes alike.
  (https://github.com/xippios/sdk-template/issues/282)
