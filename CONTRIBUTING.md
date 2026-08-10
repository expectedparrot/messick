# Contributing

Use Python 3.11 or newer. Install with `python -m pip install -e '.[dev]'`, run
`pytest`, and verify `python -m build`. Public CLI changes must preserve the
versioned envelope, stable error codes, documentation parity, and immutable
artifact semantics described in `SPEC_messick.md`.
