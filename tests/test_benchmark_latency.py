from scripts.benchmark_latency import compute_average
from scripts.benchmark_latency import compute_median
from scripts.benchmark_latency import compute_percent_reduction
from scripts.benchmark_latency import validate_runs


def test_compute_median_with_odd_number_of_values() -> None:
    assert compute_median([10.0, 30.0, 20.0]) == 20.0


def test_compute_median_with_even_number_of_values() -> None:
    assert compute_median([10.0, 40.0, 20.0, 30.0]) == 25.0


def test_compute_average_returns_mean_latency() -> None:
    assert compute_average([10.0, 20.0, 30.0]) == 20.0


def test_compute_percent_reduction_returns_expected_value() -> None:
    assert compute_percent_reduction(200.0, 50.0) == 75.0


def test_compute_percent_reduction_guards_zero_before() -> None:
    assert compute_percent_reduction(0.0, 50.0) is None


def test_validate_runs_accepts_valid_range() -> None:
    assert validate_runs(20) == 20
    assert validate_runs(30) == 30
