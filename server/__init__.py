from flask import Blueprint, Flask, render_template, make_response, app, abort, current_app, redirect, url_for
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from http import HTTPStatus
import ipaddress
import socket
import netifaces
import json
from pathlib import Path

ROOT_DIRECTORY = Path(__file__).parent.parent
TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"
TEMPLATE_NAMES = [template.name for template in Path(TEMPLATE_DIRECTORY).iterdir()]
VALID_INTERFACES = ["lo0", "tun0"]

server = Blueprint("serve", __name__, template_folder=TEMPLATE_DIRECTORY)

@dataclass
class DataStore:
    lhost: str
    lport: int

def is_valid_ipv4_address(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def get_default_lport() -> int:
    return 4444


def get_ip_address(interface: str) -> Optional[str]:
    try:
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
    except ValueError:
        return None

def get_default_lhost() -> str:
    for interface in VALID_INTERFACES:
        result = get_ip_address(interface)
        if result is not None:
            return result
    raise ValueError(
        f"Unable to get ip address for default interfaces: '{str.join(VALID_INTERFACES, ', ')}'"
    )


def get_lhost(lhost: Optional[str]) -> str:
    if lhost is None:
        return get_default_lhost()
    elif lhost in VALID_INTERFACES:
        address = get_ip_address(lhost)
        if address is None:
            raise ValueError(f"interface not found: '{lhost}'")
        return address
    elif is_valid_ipv4_address(lhost):
        return lhost
    else:
        raise ValueError(f"Unexpected lhost: '{lhost}'")


def get_datastore(lhost: Optional[str], lport: Optional[str]) -> DataStore:
    return DataStore(
        lhost=get_lhost(lhost),
        lport=(int(lport) if lport else get_default_lport()),
    )

@server.route("/shells/<template_name>")
@server.route("/shells/<template_name>/<lport>")
@server.route("/shells/<template_name>/<lhost>/<lport>")
def shell(template_name, lhost=None, lport=None):
    if template_name not in TEMPLATE_NAMES:
        return abort(HTTPStatus.IM_A_TEAPOT, description="Shell type not supported")
    payload = render_template(template_name, datastore=get_datastore(lhost, lport))
    response = make_response(payload)
    response.headers["Content-Type"] = "text/plain"
    return response


server_files = {}
config_path = Path(__file__).parent / "config.json"
with open(config_path) as config_file:
    config = json.load(config_file)
    for config_value in config:
        server_path = config_value["server_path"]
        local_path = config_value["local_path"]
        if server_path in server_files:
            raise ValueError(
                f"Duplicate server_path '{server_path}' for local_path '{local_path}'"
            )
        local_path = ROOT_DIRECTORY / local_path
        if not local_path.is_file():
            raise ValueError(f"local_path '{local_path}' is not a valid file.")

        server_files[server_path] = Path(local_path)

def get_custom_file(server_path) -> Optional[str]:
    local_path = server_files.get("/" + server_path, None)
    if local_path is None:
        return None
    with open(local_path, "r") as file:
       content = file.read()
       return content

@dataclass
class File:
    path: str
    name: str

@server.route("/")
@server.route("/<path:server_path>")
def serve_file(server_path = ""):
    custom_file = get_custom_file(server_path)
    if custom_file is not None:
        response = make_response(custom_file)
        response.headers["Content-Type"] = "text/plain"
        return response

    root_serve_directory = Path(current_app.config['ROOT_SERVE_DIRECTORY'])
    requested_path = (root_serve_directory / server_path).resolve()
    valid_child_path = (
        (root_serve_directory in requested_path.parents or requested_path == root_serve_directory)
        and requested_path.exists()
    )
    if not valid_child_path:
        return abort(HTTPStatus.NOT_FOUND)

    if requested_path.is_file():
        with open(requested_path, "rb") as file:
            content = file.read()
        response = make_response(content)
        response.headers["Content-Type"] = "text/plain"
        return response

    files = []
    for file in requested_path.iterdir():
        files.append(
            File(
                path=file.relative_to(root_serve_directory).as_posix(),
                name=file.name
            )
        )
    files.sort(key=lambda file: file.name)
    custom_files = []
    for file in server_files.keys():
        custom_files.append(
            File(
                path=file,
                name=Path(file).name
            )
        )
    custom_files.sort(key=lambda file: file.name)
    return render_template(
        "index.html",
        valid_shell_types=TEMPLATE_NAMES,
        default_lhost=get_default_lhost(),
        default_lport=get_default_lport(),
        files=files,
        custom_files=custom_files,
        server_path=server_path
    )

def serve(verbose, host, port, root_serve_directory, debug=False):
    app = Flask(__name__)
    app.config['ROOT_SERVE_DIRECTORY'] = root_serve_directory
    app.register_blueprint(server)

    app.run(host=host, port=port, debug=debug)
