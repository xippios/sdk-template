- The generated `tests/conftest.py` of a multi-tenant source says that core removes every
  tenant's variables but the reserved demo's, as conventions §7 words the strip, where it
  said every tenant's key, which a tenant's refresh token is not.
  (sdk-core ADR-0042, https://github.com/xippios/sdk-template/issues/214)
