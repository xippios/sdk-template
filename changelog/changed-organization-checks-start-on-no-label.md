- The generated `.github/workflows/organization.yml` runs on the opening, a push, a
  reopening and an edit of a pull request, no longer on `labeled`, and neither of its jobs
  has a condition of its own: GitHub reports a head's checks from its newest run, and a
  label set at the opening started a run that skipped both jobs at the caller. The callee
  tells a release pull request by its own condition, which the README of xippios/.github
  lays out, so the file's comment names no title form, and `copier update` brings the file,
  so nothing is applied by hand. The workflow has no switch of its own, so a source's first
  release after it takes 0.3.3 or later is the first pull request there whose conventions
  review runs. (https://github.com/xippios/sdk-template/issues/152)
