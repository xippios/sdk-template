- Four comments say in the repository's own words what they said of a session, the
  workspace or a person: the generated `.github/scripts/check-siblings.sh` takes a sibling
  not on PyPI from its checkout beside the repository, and this repository's `copier.yml`
  says which files a source fills and its `release.yml` that nobody pushes the tag by hand
  and that the maintainer deletes a tag a race left. `copier update` brings the script, so
  nothing is applied by hand, and the generated `publish.yml` keeps sdk-core's bytes, its
  three such lines included, until sdk-core changes them there.
  (https://github.com/xippios/sdk-template/issues/150,
  https://github.com/xippios/sdk-core/issues/215)
