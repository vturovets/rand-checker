# Random Checker

Random Checker is a configurable toolkit for evaluating the randomness of
sequence data. The project emphasises a pure Python core so it can run in
restricted environments, while offering optional accelerators when scientific
packages are available.

## Installation

The library can be installed directly from the repository or packaged with
`pip`:

```bash
pip install .
```

The default installation only relies on the Python standard library. For users
who have NumPy available and want to accelerate vector operations you can opt
into the `science` extra:

```bash
pip install .[science]
```

All vectorised code paths include pure Python fallbacks so the behaviour remains
consistent regardless of the optional dependency.

## Command line interface

After installation the `randomcheck` command is available via the console script
entry point defined in `pyproject.toml`. The CLI evaluates a dataset using the
specified configuration file:

```bash
randomcheck --input data/sample.txt --config config/example.ini
```

Use `--report` to store a markdown summary and `--verbose` for per-test
information on the console.

## Performance tooling

The `randomcheck.perf` module provides helpers to benchmark the most common data
processing stages and to capture profiling snapshots:

- `benchmark_classification(entries)` measures the throughput of entry
  classification, optimised for data sets up to 10,000 items.
- `benchmark_merge(weighted_results)` records timings for the weighted merge of
  statistical test results.
- `capture_profile()` is a context manager returning the application instance
  and a callable that renders a `cProfile` summary for any operations executed
  inside the block.
- `profile_application(input_path, config_path)` offers a quick way to profile a
  full CLI-equivalent run programmatically.

These utilities are lightweight wrappers over the Python standard library and
can be integrated into automated benchmarks or executed ad-hoc during
development.

## Testing

Run the test suite with `pytest` from the repository root:

```bash
pytest
```

The tests cover configuration parsing, input loading, statistical aggregation
and logging/report generation. Additional fixtures in `tests/` provide mock data
for sample randomness evaluations.
