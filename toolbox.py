import click
import server
from os import geteuid, path
from dataclasses import dataclass
from pathlib import Path


def validate_port_permissions(ctx, param, value):
    if value < 1024 and geteuid() != 0:
        raise click.BadParameter(f"sudo permission required to bind to port '{value}'")
    return value


def validate_root_folder(ctx, param, value):
    resolved_path = Path(value).resolve()
    valid_folder = path.exists(resolved_path) and path.isdir(resolved_path)
    if not valid_folder:
        raise click.BadParameter(f"value '{resolved_path}' is not a valid folder")
    return str(resolved_path)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind on")
@click.option(
    "--debug/--no-debug", is_flag=True, default=False, help="Enable debug mode"
)
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Enable verbose logging"
)
@click.option(
    "-p",
    "--port",
    type=click.INT,
    required=True,
    callback=validate_port_permissions,
    help="the port to serve from",
)
@click.argument("root_folder", required=True, callback=validate_root_folder)
def serve(verbose, host, port, debug, root_folder):
    server.serve(
        host=host, port=port, verbose=verbose, root_folder=root_folder, debug=debug
    )


if __name__ == "__main__":
    cli()
