# 07 — `--dry-run`

**What to build:** A way to preview a run before committing to it, which matters most before a destructive `--inplace` pass. `--dry-run` performs the full analysis and produces exactly the report a real run would, but writes nothing to disk — no destinations, no temporary files, no in-place replacements.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [x] `--dry-run` reports per-source durations before and after, and the percentage saved, as a real run would
- [x] `--dry-run` writes nothing: no destination file is created, no source is modified, no temporary file is left behind
- [x] `--dry-run` works alongside `--inplace` and `-o`, reporting what each would have done
- [x] `unchanged` outcomes are reported under `--dry-run` as they would be in a real run
- [x] The output makes clear that nothing was written
- [x] Exit codes match what the equivalent real run would produce
- [x] End-to-end tests assert the filesystem is untouched after a `--dry-run` in each destination mode

## Comments

**Implemented.** All seven criteria met.

**The reported duration is measured, not predicted.** "Reports ... as a real run would" and "writes nothing" pull against each other: the honest figure is only known after the frame-rounded cut exists. Predicting `end - start` is wrong by up to a frame, and a test confirms it — swapping the measurement for that prediction fails `test_dry_run_reports_what_a_real_run_would`.

So a dry run performs the cut for real, into the **system temporary directory** rather than beside the destination. That gives the exact figure a real run would report, while leaving nothing in the user's own directories — which matters for the same reason ticket 04 refuses to rewrite unchanged files in place: a temporary appearing and vanishing next to the source would wake every file watcher pointed at it. The temporary directory is removed on any exit path.

**The per-source lines are byte-identical to a real run's**, asserted by running both and comparing. The mode is declared by one trailing line, `dry run — nothing was written`, rather than by decorating each line, so nothing about the report changes shape between preview and reality.

**Nothing is written in any destination mode** — default, `--inplace` and `-o` are each covered, asserting both the directory listing and the source's mtime are untouched. Verified to fail if the preview path is removed.

**Review fix: a dry run reported success for runs certain to fail.** Because the cut goes to the system temporary directory, no destination write was ever attempted, so an unwritable destination — the exact thing a preview is for, before a destructive `--inplace` pass — came back clean at exit 0 while the real run exited 1. `check_writable` now confirms the destination's directory exists and is writable, without creating anything. The only exit-code test covered a corrupt *source*, which agreed by luck.
