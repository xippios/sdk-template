- The template renders no test of the row of `OBSERVED.md` in `docs/upstream/FETCHED.md`,
  since xippios-core 0.4.1's family check holds that row in every source that keeps the
  file. sdk-usda-esmis, sdk-usda-wasde, sdk-usda-esr and sdk-cashctrl delete what their
  `tests/test_observed.py` holds of the row in their patches, as core 0.4.1's changelog lists
  for each. sdk-eurostat's test of the row in `tests/test_refresh_upstream.py` holds the row
  that its own capture script writes, not the committed one, and stays with that script.
  (https://github.com/xippios/sdk-template/issues/236)
