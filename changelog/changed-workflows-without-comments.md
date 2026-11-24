- The generated `live.yml` and `siblings.yml` carry no comment but the version after a
  pinned action, as the organization decided for every workflow file, and the template's
  README says what their comments said: what each checks, when it runs, what it is handed
  and why `siblings` is a workflow of its own beside `ci.yml`. `copier update` takes the
  comments out, and `ci.yml` and `publish.yml` keep sdk-core's bytes.
  (https://github.com/xippios/.github/issues/111,
  https://github.com/xippios/sdk-template/issues/265)
