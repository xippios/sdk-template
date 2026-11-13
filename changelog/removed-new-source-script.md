- This repository no longer has `scripts/new-source.sh` or its `/new-source` command: a
  source is generated with `copier copy` from the template's URL at its latest tag, as the
  README lays out with the answers and their evidence, and `scripts/prove.sh` renders its
  proofs the same way and runs the checks itself. What the script did on GitHub, the
  repository with its topics and settings, the `pypi` environment and the first pull
  request, is left to whoever creates the repository, and a generated repository is
  unchanged. (https://github.com/xippios/sdk-template/issues/119)
