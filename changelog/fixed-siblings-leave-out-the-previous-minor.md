- The generated `.github/scripts/check-siblings.sh` leaves out a sibling that depends on the
  source and pins its previous minor, with a warning that names the pin, as it leaves out a
  sibling on another core minor: such a sibling takes the new minor in its own adoption, so
  the release of a new minor no longer fails the check, and a sibling that pins another
  minor of the source still does. `copier update` brings the script, so nothing is applied
  by hand. (https://github.com/xippios/sdk-template/issues/74)
