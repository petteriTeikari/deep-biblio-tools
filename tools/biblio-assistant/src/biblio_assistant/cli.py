"""CLI interface for biblio-assistant."""

import webbrowser
from pathlib import Path

import click
from rich.console import Console

from .core.server import BiblioServer
from .utils.config import load_config

console = Console()


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Web-based interface for interactive bibliography management."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(
        ["all", "validator", "processor", "reviewer", "converter"]
    ),
    default="all",
    help="Start in specific mode",
)
@click.option(
    "--no-browser", is_flag=True, help="Do not open browser automatically"
)
@click.option("--debug", is_flag=True, help="Run in debug mode")
@click.pass_context
def serve(ctx, host, port, mode, no_browser, debug):
    """Start the web server."""
    config = ctx.obj.get("config", {})

    # Override config with command line options
    config.setdefault("server", {})
    config["server"]["host"] = host
    config["server"]["port"] = port
    config["server"]["debug"] = debug
    config["server"]["mode"] = mode

    # Create and start server
    server = BiblioServer(config)

    console.print(
        "[bold green]Starting Biblio Assistant server...[/bold green]"
    )
    console.print(f"[dim]Mode: {mode}[/dim]")
    console.print(f"[dim]URL: http://{host}:{port}[/dim]")

    # Open browser if requested
    if not no_browser:
        import threading
        import time

        def open_browser():
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["validate", "process", "convert"]),
    help="Processing mode",
)
@click.pass_context
def process(ctx, file_path, mode):
    """Process a file through the web interface."""
    config = ctx.obj.get("config", {})

    # Start server in background
    server = BiblioServer(config)

    import threading

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to start
    import time

    time.sleep(1)

    # Open browser with file pre-loaded
    file_abs = Path(file_path).absolute()

    if mode == "validate":
        url = f"http://localhost:8000/validate?file={file_abs}"
    elif mode == "process":
        url = f"http://localhost:8000/process?file={file_abs}"
    elif mode == "convert":
        url = f"http://localhost:8000/convert?file={file_abs}"
    else:
        url = f"http://localhost:8000/?file={file_abs}"

    console.print(
        f"[bold blue]Opening {file_path} in web interface...[/bold blue]"
    )
    webbrowser.open(url)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Processing stopped[/yellow]")


@cli.command()
@click.argument("bibliography", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "detailed", "json"]),
    default="summary",
    help="Report format",
)
@click.pass_context
def validate(ctx, bibliography, format):
    """Validate a bibliography file."""
    # This is a convenience command that uses the web UI
    ctx.invoke(process, file_path=bibliography, mode="validate")


@cli.command()
@click.pass_context
def info(ctx):
    """Show information about the web interface."""
    config = ctx.obj.get("config", {})

    console.print("[bold]Biblio Assistant Information[/bold]\n")

    console.print("[bold cyan]Server Configuration:[/bold cyan]")
    server_config = config.get("server", {})
    console.print(f"  Host: {server_config.get('host', '127.0.0.1')}")
    console.print(f"  Port: {server_config.get('port', 8000)}")
    console.print(f"  Debug: {server_config.get('debug', False)}")

    console.print("\n[bold cyan]Available Tools:[/bold cyan]")
    tools = [
        ("Citation Validator", "Validate citations against databases"),
        ("Paper Processor", "Extract content from papers"),
        ("Literature Reviewer", "Generate literature reviews"),
        ("Format Converter", "Convert between formats"),
        ("Quality Guardian", "Check writing quality"),
    ]

    for tool, desc in tools:
        console.print(f"  • {tool}: {desc}")

    console.print("\n[bold cyan]API Endpoints:[/bold cyan]")
    endpoints = [
        ("GET /", "Web interface home"),
        ("POST /api/validate", "Validate citations"),
        ("POST /api/process", "Process paper"),
        ("POST /api/convert", "Convert format"),
        ("POST /api/review", "Generate review"),
        ("GET /api/status", "Server status"),
    ]

    for endpoint, desc in endpoints:
        console.print(f"  {endpoint:<25} {desc}")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
