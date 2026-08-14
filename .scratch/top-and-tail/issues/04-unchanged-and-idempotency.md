# 04 — Unchanged outcomes and idempotency

**What to build:** Correct behaviour when there is nothing to strip. A source with no leading or trailing silence is reported as `unchanged` and exits successfully — it is not an error. So is a source that is silent throughout: it is left alone rather than truncated to nothing, because a silent file is almost certainly a failed generation the user will want to inspect.

An `unchanged` outcome still writes the destination, as an exact copy of the source, so the output set is complete regardless of which sources needed work. The single exception is `--inplace`, where an unchanged source is left completely untouched — no rewrite, no mtime change — so that file watchers and sync clients are not triggered by a no-op.

Together these make the tool idempotent: running it a second time over its own output reports `unchanged` and alters nothing.

**Blocked by:** 01, 03

**Status:** ready-for-agent

- [ ] A source with no leading or trailing silence is reported as `unchanged` and exits zero
- [ ] A source that is silent throughout is reported as `unchanged` and is never truncated
- [ ] An `unchanged` outcome still writes the destination as an exact copy of the source
- [ ] Under `--inplace`, an `unchanged` source is not rewritten and its mtime does not change
- [ ] `unchanged` sources appear in the report rather than being hidden, so a repeat run visibly confirms idempotency
- [ ] A batch of entirely `unchanged` sources exits zero
- [ ] An end-to-end test runs the tool over its own output and asserts the result is byte-identical to the first run
