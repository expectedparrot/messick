"""Messick CLI — tiered response validation for EDSL studies."""
from __future__ import annotations

import sys

import typer

from messick.packaged_docs import load_agent, load_readme

app = typer.Typer(
    name="messick",
    help="Tiered response validation for EDSL studies.",
    add_completion=False,
)


@app.command()
def agent() -> None:
    typer.echo(load_agent())


@app.command()
def readme() -> None:
    typer.echo(load_readme())


@app.command(
    name="validate",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def validate(ctx: typer.Context) -> None:
    """Run the validation pipeline. Flags forwarded to the underlying script.

    Run `messick validate --help` for the full set of arguments.
    """
    from messick import core

    saved_argv = sys.argv
    sys.argv = ["messick-validate", *ctx.args]
    try:
        core.main()
    except SystemExit as e:
        raise typer.Exit(code=int(e.code) if e.code is not None else 0)
    finally:
        sys.argv = saved_argv


def main() -> None:
    app()


if __name__ == "__main__":
    main()
