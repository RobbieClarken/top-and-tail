# top-and-tail

Strip leading and trailing silence from MP3 files, without touching the audio
in between and without re-encoding.

## Requirements

- `ffmpeg` and `ffprobe` on your `PATH`
- [`uv`](https://docs.astral.sh/uv/), and Python 3.13 or newer.

## Install

`top-and-tail` is a single executable file with a `uv run --script` shebang.
Symlink it onto your `PATH`; there is no packaging step and no virtual
environment to activate.

```bash
ln -s "$PWD/top-and-tail" ~/.local/bin/top-and-tail
```

## Usage

By default each result is written beside its source as `<name>.stripped.mp3`.

```console
$ top-and-tail hablar.mp3
hablar.mp3  1.92s → 0.69s  (-64%)
```

Pass several sources:

```console
$ top-and-tail yo.mp3 pretérito.mp3 él.mp3
yo.mp3  1.04s → 0.48s  (-54%)
pretérito.mp3  2.48s → 0.82s  (-67%)
él.mp3  1.44s → 0.38s  (-74%)
3 files  4.96s → 1.68s  (-66%)
```

An existing `<name>.stripped.mp3` is overwritten without prompting.

Use `-n` / `--dry-run` to preview the results:

```console
$ top-and-tail --dry-run yo.mp3 pretérito.mp3 él.mp3
yo.mp3  1.04s → 0.48s  (-54%)
pretérito.mp3  2.48s → 0.82s  (-67%)
él.mp3  1.44s → 0.38s  (-74%)
3 files  4.96s → 1.68s  (-66%)
dry run — nothing was written
```

### Options

| Option                  | Default | Effect                                                                  |
| ----------------------- | ------- | ----------------------------------------------------------------------- |
| `--in-place`            | off     | Replace each source with its stripped result, atomically.               |
| `-o`, `--output OUTPUT` | —       | Write the result to this path. One source only.                         |
| `-n`, `--dry-run`       | off     | Report what would happen and write nothing.                             |
| `--threshold DBFS`      | `-50.0` | Below this amplitude counts as quiet audio.                             |
| `--min-silence SECONDS` | `0.1`   | How long quiet audio must last before it counts as silence.             |
| `--padding SECONDS`     | `0.05`  | Silence deliberately kept at each end, so a word's onset isn't clipped. |

`--in-place` and `-o` are mutually exclusive.

## Development

```bash
uv run pytest   # tests
uv run mypy     # typechecker
```
