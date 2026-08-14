"""Seam 2: the pure boundary arithmetic, tested with synthetic samples."""

from pytest import approx

from conftest import LOUD, QUIET, UNIT_RATE, samples, tool

THRESHOLD_DB = -50.0
MIN_SILENCE = 0.010
PADDING = 0.005


def bounds(buffer, min_silence=MIN_SILENCE, padding=PADDING, threshold_db=THRESHOLD_DB):
    return tool.find_bounds(
        buffer,
        sample_rate=UNIT_RATE,
        threshold_db=threshold_db,
        min_silence=min_silence,
        padding=padding,
    )


def test_buffer_with_no_silence_keeps_everything():
    assert bounds(samples((LOUD, 100))) == (0.0, 0.100)


def test_trailing_silence_is_stripped_back_to_padding():
    # 50 samples of utterance, then 20 of silence: the cut keeps 5 of padding.
    assert bounds(samples((LOUD, 50), (QUIET, 20))) == approx((0.0, 0.055))


def test_leading_silence_is_stripped_back_to_padding():
    assert bounds(samples((QUIET, 20), (LOUD, 50))) == approx((0.015, 0.070))


def test_quiet_shorter_than_the_minimum_run_is_not_silence():
    # 9 samples of quiet against a 10-sample minimum run: nothing is stripped.
    assert bounds(samples((LOUD, 50), (QUIET, 9))) == approx((0.0, 0.059))


def test_quiet_exactly_at_the_minimum_run_is_silence():
    assert bounds(samples((LOUD, 50), (QUIET, 10))) == approx((0.0, 0.055))


def test_internal_silence_is_never_stripped():
    buffer = samples((LOUD, 20), (QUIET, 30), (LOUD, 20))
    assert bounds(buffer) == approx((0.0, 0.070))


def test_internal_silence_survives_while_both_ends_are_stripped():
    buffer = samples((QUIET, 20), (LOUD, 10), (QUIET, 30), (LOUD, 10), (QUIET, 20))
    assert bounds(buffer) == approx((0.015, 0.075))


def test_padding_is_clamped_at_the_start_of_the_buffer():
    buffer = samples((QUIET, 12), (LOUD, 20))
    assert bounds(buffer, padding=0.030) == approx((0.0, 0.032))


def test_padding_is_clamped_at_the_end_of_the_buffer():
    buffer = samples((LOUD, 20), (QUIET, 12))
    assert bounds(buffer, padding=0.030) == approx((0.0, 0.032))


def test_samples_just_below_the_threshold_are_quiet():
    # -50 dBFS of a 32768 full scale is a magnitude of 103.6.
    assert bounds(samples((103, 20), (LOUD, 20))) == approx((0.015, 0.040))
    assert bounds(samples((-103, 20), (LOUD, 20))) == approx((0.015, 0.040))


def test_samples_just_above_the_threshold_are_not_quiet():
    assert bounds(samples((104, 20), (LOUD, 20))) == approx((0.0, 0.040))


def test_a_buffer_that_is_silent_throughout_has_no_utterance():
    assert bounds(samples((QUIET, 100))) is None
