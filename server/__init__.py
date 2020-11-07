from flask import Blueprint, Flask, render_template, make_response, app, abort
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from http import HTTPStatus
import ipaddress
import socket
import netifaces

server = Blueprint("serve", __name__, template_folder="./templates")

VALID_SHELL_TYPES = ["py", "sh", "php", "js"]
VALID_INTERFACES = ["lo0", "tun0"]


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


@server.route("/", methods=["GET"])
@server.route("/shells", methods=["GET"])
def index():
    return render_template(
        "index.html",
        valid_shell_types=VALID_SHELL_TYPES,
        default_lhost=get_default_lhost(),
        default_lport=get_default_lport(),
    )


@server.route("/shells/<shell_type>")
@server.route("/shells/<shell_type>/<lport>")
@server.route("/shells/<shell_type>/<lhost>/<lport>")
def shell(shell_type, lhost=None, lport=None):
    if shell_type not in VALID_SHELL_TYPES:
        abort(HTTPStatus.IM_A_TEAPOT, description="Shell type not supported")
    template_name = f"shell.{shell_type}"
    payload = render_template(template_name, datastore=get_datastore(lhost, lport))
    response = make_response(payload)
    response.headers["Content-Type"] = "text/plain"
    return response


def serve(verbose, host, port, root_folder, debug=False):
    app = Flask(__name__)
    app.register_blueprint(server)

    app.run(host=host, port=port, debug=debug)
