# 04 — Unchanged outcomes and idempotency

**What to build:** Correct behaviour when there is nothing to strip. A source with no leading or trailing silence is reported as `unchanged` and exits successfully — it is not an error. So is a source that is silent throughout: it is left alone rather than truncated to nothing, because a silent file is almost certainly a failed generation the user will want to inspect.

An `unchanged` outcome still writes the destination, as an exact copy of the source, so the output set is complete regardless of which sources needed work. The single exception is `--inplace`, where an unchanged source is left completely untouched — no rewrite, no mtime change — so that file watchers and sync clients are not triggered by a no-op.

Together these make the tool idempotent: running it a second time over its own output reports `unchanged` and alters nothing.

**Blocked by:** 01, 03

**Status:** ready-for-agent

- [x] A source with no leading or trailing silence is reported as `unchanged` and exits zero
- [x] A source that is silent throughout is reported as `unchanged` and is never truncated
- [x] An `unchanged` outcome still writes the destination as an exact copy of the source
- [x] Under `--inplace`, an `unchanged` source is not rewritten and its mtime does not change
- [x] `unchanged` sources appear in the report rather than being hidden, so a repeat run visibly confirms idempotency
- [x] A batch of entirely `unchanged` sources exits zero
- [x] An end-to-end test runs the tool over its own output and asserts the result is byte-identical to the first run

## Comments

**Implemented.** All seven criteria met; 49 tests pass, mypy clean.

**The "don't rewrite under `--inplace`" rule was queried as possibly not worth its complexity. It costs nothing.** `shutil.copy2` raises `SameFileError` when the destination is the source, so the code must branch on that case whichever semantics are chosen — and skipping the write is the simpler arm. Removing the guard doesn't simplify the implementation, it crashes: four tests fail with `SameFileError`. `CONTEXT.md` is unchanged.

**Unchanged means two things**, both handled at one place: a source that is silent throughout, and one whose quiet is too brief to be silence. Detected as `find_bounds` returning `None`, or returning bounds that span the whole buffer.

**Unchanged destinations are exact byte copies**, via `copy2`, not frame copies. A frame copy would round to the nearest frame and change the bytes; `test_a_silent_source_is_unchanged_and_never_truncated` fails if that path is used instead.

**`test_a_rerun_never_reports_the_file_growing` from ticket 02 was rewritten.** It parsed `before → after` out of the report and asserted the file hadn't grown. A rerun now reports `unchanged` and prints no arrow at all, so the regex stopped matching. The replacement asserts the stronger property directly. The measurement-consistency concern it originally guarded is still pinned by the exact `1.92s → 0.69s` assertions on a first run.

**The summary line also collapses to `unchanged`** when every source in a batch was unchanged, rather than reporting `(+0%)`.

**Review fixes — two real bugs, both from the unchanged path bypassing the writer.**

*File mode.* `write_atomically` deliberately keeps the destination's existing mode, but `keep_unchanged` used `shutil.copy2`, which stamps the **source's** mode instead. Measured: a 0600 destination became 0644 via the unchanged path and stayed 0600 via the stripped one — two rules for the one spec sentence. The unchanged path also truncated in place, so it lacked the atomicity the stripped path has.

Both fixed by routing every write through a single `place()` function that takes a producer — frame copy or byte copy. One set of rules for mode, atomicity and cleanup.

*Same-file detection compared paths, not files.* `destination != source.resolve()` resolves symlinks but not hard links, so a hardlinked destination was not recognised as the source. On its own that raised `SameFileError`; once every write went through `place()` the crash disappeared, but the file was still needlessly rewritten — renaming a fresh file over one of the two names, breaking the link and bumping the mtime for a file that needed no work. Now `os.path.samefile`, which covers identity, symlinks and hard links.

Worth recording how that was caught: the first version of the hardlink test passed against the reverted code, because `place()` had already removed the crash it asserted on. Asserting the link survives and the mtime holds gave it teeth.

**Test cleanups from review:** the two unchanged-report tests were the same test twice, so one went; `make_silent_mp3` moved up with the other helpers; an unused `hablar` fixture dropped; and `stdout.count("unchanged") == 4` replaced with an assertion that every reported line ends in `unchanged`, which does not silently pin the summary-collapse behaviour.

**Known limitation, not fixed.** When a source *does* need stripping and the destination is a hard link to it, the atomic rename necessarily breaks the link: the destination name gets the stripped file, the other name keeps the original. Writing into the shared inode instead would preserve the link but give up atomicity. Symlinks do not have this problem because destinations are resolved. Flagging rather than deciding.

**Noted but not changed:** `strip` detects "nothing to strip" by comparing `find_bounds`' result against the whole buffer, which recomputes arithmetic `find_bounds` could report itself. The comparison is bit-exact today because both sides are the identical expression. Worth folding into `find_bounds` if that return type gains a fourth state.
