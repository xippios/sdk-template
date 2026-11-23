from xippios.core.testing.built_answers import *  # noqa: F403

# What core's check of a built answer's mark reads from this module (conventions §10,
# sdk-core ADR-0049), both the source's: READERS, the names of its own functions that take a
# body written in a test, judged as a scrub is, and ALLOWED, a helper or test whose places
# are neither a kind of §10 nor an input of the test, ("tests/<module>.py", "<top-level
# definition>") mapped to its reason.
READERS: frozenset[str] = frozenset()
ALLOWED: dict[tuple[str, str], str] = {}
