- Template-internal, the tests: the variants' answers, their renders and the helpers the
  tests share move unchanged from `tests/test_template.py` into `tests/conftest.py` and
  `tests/helpers.py`, so a new concern's tests take a module of their own. No rendered
  file changes, and a generated repository takes nothing at its update.
  (https://github.com/xippios/sdk-template/issues/181)
