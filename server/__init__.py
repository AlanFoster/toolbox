from flask import Blueprint, Flask, render_template, make_response, app, abort
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

        server_files[server_path] = {
            "server_path": server_path,
            "local_path": local_path,
        }


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


@server.route("/")
@server.route("/", methods=["GET"])
@server.route("/shells", methods=["GET"])
def index():
    return render_template(
        "index.html",
        valid_shell_types=TEMPLATE_NAMES,
        default_lhost=get_default_lhost(),
        default_lport=get_default_lport(),
        server_files=server_files.values(),
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


@server.route("/<server_path>")
def serve_file(server_path):
    config_value = server_files.get("/" + server_path, None)
    if config_value is None:
        return abort(HTTPStatus.NOT_FOUND, description="file not found")
    local_path = config_value["local_path"]
    with open(local_path, "r") as file:
        content = file.read()
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response


def serve(verbose, host, port, root_folder, debug=False):
    app = Flask(__name__)
    app.register_blueprint(server)

    app.run(host=host, port=port, debug=debug)
