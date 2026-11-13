- The generated `live.yml` runs the live tests with `--assert=plain` beside `--tb=short`, so
  a failed assertion prints its line and `AssertionError` in the run's log, never the values
  it compared, a record of the upstream among them. `copier update` brings it, so nothing is
  applied by hand. (https://github.com/xippios/sdk-template/issues/58)
