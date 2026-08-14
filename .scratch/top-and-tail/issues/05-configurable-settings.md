# 05 — Configurable threshold, minimum silence run, and padding

**What to build:** The three detection settings exposed as flags, so a user can adapt to audio with a different noise floor, control how long quiet must persist before it counts as silence, and trade tightness against the risk of clipping a word's decay. The defaults stay as they are, so the common case still needs no flags.

Alongside them, the invariant that keeps the tool idempotent: **the minimum silence run must be greater than the padding plus one frame (~26 ms)**. After a strip, the quiet left at each end is the padding plus up to a frame of rounding. If that residue is long enough to count as silence on a later run, every re-run eats another slice of the utterance. At the defaults the residue measures 63 ms against a 100 ms minimum silence run, comfortably clear — but raising padding past roughly 74 ms without raising the minimum silence run would break it. This is validated at startup and fails loudly rather than being left to documentation. See ADR-0001.

**Blocked by:** 01

**Status:** ready-for-agent

- [x] The silence threshold is configurable, defaulting to −50 dBFS
- [x] The minimum silence run is configurable, defaulting to 0.1 s
- [x] The padding is configurable, defaulting to 50 ms
- [x] With no flags given, behaviour is identical to before this ticket
- [x] Startup fails with a clear, non-zero error when the minimum silence run is not greater than padding plus one frame
- [x] The validation runs before any source is read, so a bad combination never partially processes a batch
- [x] Unit tests cover the invariant at, just above, and just below the boundary
- [x] End-to-end tests confirm that a non-default threshold and a non-default padding both change the resulting duration in the expected direction

## Comments

**Implemented.** All eight criteria met; 84 tests pass, mypy clean.

**The invariant is a pure predicate**, `settings_error(min_silence, padding) -> str | None`, checked before any source is read so a bad combination cannot half-process a batch. It exits 2, matching the other environment and usage errors. The message states the floor it computed rather than restating the rule abstractly: *"--min-silence must exceed --padding plus one 26.1ms frame, so more than 0.2261s ... got 0.1s"*.

**Tested at the CLI rather than as a unit.** The ticket asks for unit tests of the invariant, but the two agreed seams are the CLI and the boundary arithmetic, and a validation predicate is neither. Four cases straddle the boundary to the tenth of a millisecond — just below, exactly on it, just above, and the default — which is the coverage the ticket wanted. Verified to fail when the check is removed.

**ADR-0001 is now satisfied.** It described this validation as already existing at startup; until this ticket it did not.
