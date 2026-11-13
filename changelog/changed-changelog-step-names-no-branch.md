- The changelog step of the generated `ci.yml` exempts Dependabot's branch alone and tells a
  release by no branch name: a release's pull request changes `CHANGELOG.md` and passes as
  any other does. `copier update` brings it, so nothing is applied by hand.
  (https://github.com/xippios/sdk-template/issues/136)
