# 05 — Configurable threshold, minimum silence run, and padding

**What to build:** The three detection settings exposed as flags, so a user can adapt to audio with a different noise floor, control how long quiet must persist before it counts as silence, and trade tightness against the risk of clipping a word's decay. The defaults stay as they are, so the common case still needs no flags.

Alongside them, the invariant that keeps the tool idempotent: **the minimum silence run must be greater than the padding plus one frame (~26 ms)**. After a strip, the quiet left at each end is the padding plus up to a frame of rounding. If that residue is long enough to count as silence on a later run, every re-run eats another slice of the utterance. At the defaults the residue measures 63 ms against a 100 ms minimum silence run, comfortably clear — but raising padding past roughly 74 ms without raising the minimum silence run would break it. This is validated at startup and fails loudly rather than being left to documentation. See ADR-0001.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The silence threshold is configurable, defaulting to −50 dBFS
- [ ] The minimum silence run is configurable, defaulting to 0.1 s
- [ ] The padding is configurable, defaulting to 50 ms
- [ ] With no flags given, behaviour is identical to before this ticket
- [ ] Startup fails with a clear, non-zero error when the minimum silence run is not greater than padding plus one frame
- [ ] The validation runs before any source is read, so a bad combination never partially processes a batch
- [ ] Unit tests cover the invariant at, just above, and just below the boundary
- [ ] End-to-end tests confirm that a non-default threshold and a non-default padding both change the resulting duration in the expected direction
