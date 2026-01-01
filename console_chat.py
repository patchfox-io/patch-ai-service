#!/usr/bin/env python3
import socket
import sys

from rich.console import Console
from rich.prompt import Prompt
from rich.status import Status
from rich.panel import Panel

HOST = "127.0.0.1"
PORT = 8765

console = Console()

def recv_line(sock: socket.socket) -> str | None:
    """Read until newline. Returns None if disconnected."""
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None
        if chunk == b"\n":
            return buf.decode(errors="replace")
        buf.extend(chunk)

def main():
    console.print(Panel.fit("Patch Console Chat", style="bold green"))

    try:
        sock = socket.create_connection((HOST, PORT))
    except Exception as e:
        console.print(f"[red]Failed to connect:[/red] {e}")
        sys.exit(1)

    console.print(f"[dim]Connected to {HOST}:{PORT}[/dim]\n")

    # IMPORTANT: do NOT use `with sock:` in a way that ends early.
    # Keep this socket alive for the whole REPL.
    try:
        while True:
            try:
                msg = Prompt.ask("[bold cyan]>[/bold cyan]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]bye[/dim]")
                break

            msg = msg.strip()
            if not msg:
                continue

            sock.sendall((msg + "\n").encode())

            # Wait for at least one response line
            with Status("[yellow]Waiting…[/yellow]", spinner="dots", console=console):
                line = recv_line(sock)
                if line is None:
                    console.print("[red]Disconnected[/red]")
                    return
                if line.strip():
                    console.print(Panel(line.rstrip(), style="white"))

                # Drain any additional lines that arrive quickly (optional)
                sock.settimeout(0.2)
                while True:
                    try:
                        more = recv_line(sock)
                        if more is None:
                            console.print("[red]Disconnected[/red]")
                            return
                        if more.strip():
                            console.print(Panel(more.rstrip(), style="white"))
                    except socket.timeout:
                        break
                sock.settimeout(None)

    finally:
        try:
            sock.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
