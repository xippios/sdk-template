- The generated `scripts/refresh_reference.py` passes `render_enums` no class names of its
  own: core 0.4.0's default names an id list's class after its id field, a camelCase hump
  kept, `unitId` making `UnitId`, as the script's own line did for every id field the
  sources render. A class name set by hand goes to `render_enums(class_names=...)`.
  (ADR-0031, https://github.com/xippios/sdk-template/issues/167)
  - Hand-apply: `scripts/refresh_reference.py` — in `render`, delete the dict
    `class_names`, its line `class_names[id_field] = id_field[:1].upper() + id_field[1:]`
    and the argument `class_names=class_names`, keep a name the source sets by hand, such
    as sdk-usda-nass's `ProgressStage`, in a `class_names=` argument of its own, and see
    `--render-only` write `enums.py` unchanged — core's default gives the line's name for
    an id field in camelCase with no upper-case run and no separator, as `unitId` and
    `attributeId` are, and its own for another, `countryISO` making `CountryIso`.
