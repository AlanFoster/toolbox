import click
from toolbox import __version__
from toolbox.server import server

from os import geteuid, path
from pathlib import Path


def validate_port_permissions(ctx, param, value):
    if value < 1024 and geteuid() != 0:
        raise click.BadParameter(f"sudo permission required to bind to port '{value}'")
    return value


def validate_directory(ctx, param, value):
    resolved_path = Path(value).resolve()
    valid_directory = path.exists(resolved_path) and path.isdir(resolved_path)
    if not valid_directory:
        raise click.BadParameter(f"value '{resolved_path}' is not a valid folder")
    return str(resolved_path)


@click.version_option(__version__)
@click.group()
def cli():
    pass

import selectors
from queue import Queue

sel = selectors.DefaultSelector()

import code
import readline
import rlcompleter


# TODO List:
#   - Readline / history support
#   - upload / download file functionality
#   - Being able to kill a program without... killing a program

# https://sites.google.com/site/xiangyangsite/home/technical-tips/software-development/python/python-readline-completions
def completer(text, state):
    try:
        available = [
            "eyoo",
            "eyo",
            "eyooo2",
            "foo",
            "foobar",
            "foobarbaz",
            "qux"
        ]
        elements = [x for x in available if x.startswith(text)]

        if state >= len(elements):
            return None

        # print(f"text={text} state={state}")
        return elements[state]
    except Exception as e:
        print(e)

import threading
import socket
import selectors
import sys
from queue import Queue

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind on")
@click.option(
    "-p",
    "--port",
    type=click.INT,
    required=True,
    callback=validate_port_permissions,
    help="the port to serve from",
)
def listener(host, port):
    write_queue = Queue()
    socket_listener_thread = threading.Thread(target=socket_listener_thread_loop, args=(host, port, write_queue))
    socket_listener_thread.start()

    while True:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")
        readline.set_completer(completer)

        line = input("> ")
        if line == "quit":
            break

        write_queue.put(f"{line}\n")

    # while True:
    #     # result = sys.stdin.readline()
    #     # print(result)

    #     line = input("Prompt ('stop' to quit): ")
    #     if line == "quit":
    #         break

    #     print(f"entered {line}")

    # vars = globals()
    # vars.update(locals())

    # readline.set_completer(rlcompleter.Completer(vars).complete)
    # readline.parse_and_bind("tab: complete")
    # code.InteractiveConsole(vars).interact()

def socket_listener_thread_loop(host, port, write_queue):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.setblocking(False)

    listener_backlog = 1
    sock.listen(listener_backlog)

    sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, (accept, write_queue,))
    # sel.register(sys.stdin, selectors.EVENT_READ, handle_user_input)

    while True:
        events = sel.select()
        for key, mask in events:
            callback, write_queue = key.data
            callback((key.fileobj, write_queue), mask)
    # shutdown
    # sel.unregister()

def accept(data, mask):
    sock, write_queue = data
    conn, addr = sock.accept()
    print('accepted', conn, 'from', addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, (handle_shell_update, write_queue,))

def handle_shell_update(data, mask):
    conn, write_queue = data

    if mask & selectors.EVENT_READ:
        data = conn.recv(1000)
        if data:
            print(data.decode(encoding="utf-8"))
        else:
            print('closing', conn)
            sel.unregister(conn)
            conn.close()
    if mask & selectors.EVENT_WRITE:
        if not write_queue.empty():
            message = write_queue.get()

            conn.sendall(message.encode(encoding="utf-8"))

# def handle_user_input(stream, mask):
#     if mask & selectors.EVENT_READ:
#         write_queue.append(stream.readline())

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind on")
@click.option(
    "--debug/--no-debug",
    is_flag=True,
    default=False,
    help="Enable debug mode. Note this exposes `/console` which could potentially be accessed remotely and access could be bruteforced.",
)
@click.option(
    "--reload/--no-reload",
    is_flag=True,
    default=False,
    help="Enable reloading of files. This includes python files *and* python files",
)
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Enable verbose logging"
)
@click.option(
    "--password",
    required=False,
    default=None,
    help="A password is required to upload files. There is no username.",
)
@click.option(
    "-p",
    "--port",
    type=click.INT,
    required=True,
    callback=validate_port_permissions,
    help="the port to serve from",
)
@click.argument("root_user_directory", required=True, callback=validate_directory)
def serve(host, port, password, debug, reload, verbose, root_user_directory):
    root_toolbox_directory = Path(__file__).parent.parent

    server.serve(
        host=host,
        port=port,
        verbose=verbose,
        password=password,
        root_toolbox_directory=root_toolbox_directory,
        root_user_directory=root_user_directory,
        config_path=Path(__file__).parent / "config.json",
        use_debugger=debug,
        use_reloader=reload,
    )


def run():
    cli()


if __name__ == "__main__":
    run()
