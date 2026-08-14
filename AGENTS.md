# AGENTS.md

## Development

- Run the tests: `uv run pytest`
- Run the typechecker: `uv run mypy` (configured in `pyproject.toml`; the tool is checked under `--strict`, test functions are exempt from annotation requirements but their bodies are still checked)
- Run the tool: `./top-and-tail <source.mp3> [<source.mp3> ...]`

Both `ffmpeg` and `ffprobe` must be on `PATH` — ffmpeg decodes and copies frames, ffprobe supplies the durations in the report. The tool itself has no third-party runtime dependencies — `pytest`, `mutagen` and `mypy` are development dependencies only, and `mutagen` is permitted in tests as an independent oracle but never in the tool.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, unchanged — recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
