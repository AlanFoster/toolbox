from flask import (
    Blueprint,
    Flask,
    render_template,
    make_response,
    app,
    abort,
    current_app,
    request,
    redirect,
    url_for,
)
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from http import HTTPStatus
import ipaddress
import socket
import netifaces
import json
from pathlib import Path
from typing import TypeVar, List
from collections.abc import Mapping

import pkgutil

# TOOD: Rip these out
ROOT_DIRECTORY = Path(__file__).parent.parent.parent
TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"
TEMPLATE_NAMES = [template.name for template in Path(TEMPLATE_DIRECTORY).iterdir()]

server = Blueprint("serve", __name__, template_folder=TEMPLATE_DIRECTORY)

ServerPath = str
LocalPath = str
ServerPathMap = Mapping[ServerPath, LocalPath]


class ServerConfig:
    def __init__(self, config_path: str):
        self.server_files: ServerPathMap = self._parse_config(config_path)

    def get_local_path(self, server_path: ServerPath) -> Optional[LocalPath]:
        return self.server_files.get(server_path, None)

    def server_paths(self) -> List[ServerPath]:
        return self.server_files.keys()

    def _parse_config(self, config_path: str) -> ServerPathMap:
        server_files = {}
        with open(config_path) as config_file:
            config = json.load(config_file)

        for config_value in config["server"]:
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
        return server_files


@dataclass
class DataStore:
    lhost: str
    lport: int
    srvhost_url: str


class PayloadGenerator:
    VALID_INTERFACES = ["tun0", "lo", "lo0"]

    def __init__(self, config_path: str):
        self.config_path = config_path

    def generate(self, name: str, lhost: Optional[str], lport: Optional[str]) -> str:
        # TODO: Don't rely on render_template
        payload = render_template(name, datastore=self._get_datastore(lhost, lport))
        return payload

    def __contains__(self, name):
        return name in TEMPLATE_NAMES

    @property
    def default_lport(self) -> int:
        return 4444

    @property
    def default_lhost(self) -> str:
        for interface in PayloadGenerator.VALID_INTERFACES:
            result = self._get_ip_address(interface)
            if result is not None:
                return result
        raise ValueError(
            f"Unable to get ip address for default interfaces: '{str.join(VALID_INTERFACES, ', ')}'"
        )

    def _get_datastore(self, lhost: Optional[str], lport: Optional[str]) -> DataStore:
        return DataStore(
            lhost=(lhost if lhost else self.default_lhost),
            lport=(int(lport) if lport else self.default_lport),
            # TODO: Add a cleaner way of doing this
            srvhost_url=request.host_url,
        )

    def _is_valid_ipv4_address(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _get_ip_address(self, interface: str) -> Optional[str]:
        try:
            return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
        except ValueError:
            return None

    def _get_lhost(self, lhost: Optional[str]) -> str:
        if lhost is None:
            return self.default_lhost()

        if lhost in PayloadGenerator.VALID_INTERFACES:
            address = self._get_ip_address(lhost)
            if address is None:
                raise ValueError(f"interface not found: '{lhost}'")
            return address

        if self.is_valid_ipv4_address(lhost):
            return lhost

        raise ValueError(f"Unexpected lhost: '{lhost}'")


@dataclass
class File:
    path: str
    name: str


class FileServer:
    def __init__(
        self, server_config: ServerConfig, payload_generator: PayloadGenerator
    ):
        self.server_config = server_config
        self.payload_generator = payload_generator

    def serve(self, server_path: ServerPath):
        custom_file = self._get_custom_file(server_path)
        if custom_file is not None:
            response = make_response(custom_file)
            response.headers["Content-Type"] = "text/plain"
            return response

        root_serve_directory = Path(current_app.config["ROOT_SERVE_DIRECTORY"])
        requested_path = (root_serve_directory / server_path).resolve()
        # Ensure arbitrary file reads can't occur
        valid_child_path = (
            root_serve_directory in requested_path.parents
            or requested_path == root_serve_directory
        ) and requested_path.exists()
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
                    name=file.name,
                )
            )
        files.sort(key=lambda file: file.name)
        custom_files = []
        for file in self.server_config.server_paths():
            custom_files.append(File(path=file, name=Path(file).name))
        custom_files.sort(key=lambda file: file.name)

        return render_template(
            "index.html",
            valid_shell_types=TEMPLATE_NAMES,
            default_lhost=self.payload_generator.default_lhost,
            default_lport=self.payload_generator.default_lport,
            files=files,
            custom_files=custom_files,
            server_path=server_path,
        )

    def _get_custom_file(self, server_path: ServerPath) -> Optional[str]:
        local_path = self.server_config.get_local_path("/" + server_path)
        if local_path is None:
            return None

        with open(local_path, "r") as file:
            content = file.read()
            return content


@server.route("/shells/<name>")
@server.route("/shells/<name>/<lport>")
@server.route("/shells/<name>/<lhost>/<lport>")
def shell(name: str, lhost: Optional[str] = None, lport: Optional[str] = None):
    payload_generator = PayloadGenerator(config_path=current_app.config["CONFIG_PATH"])
    if name not in payload_generator:
        return abort(HTTPStatus.IM_A_TEAPOT, description="Shell type not supported")
    payload = payload_generator.generate(name=name, lhost=lhost, lport=lport)
    response = make_response(payload)
    response.headers["Content-Type"] = "text/plain"
    return response


@server.route("/")
@server.route("/<path:server_path>")
def serve_file(server_path=""):
    payload_generator = PayloadGenerator(config_path=current_app.config["CONFIG_PATH"])
    server_config = ServerConfig(config_path=current_app.config["CONFIG_PATH"])
    file_server = FileServer(
        server_config=server_config, payload_generator=payload_generator
    )

    return file_server.serve(server_path)


def serve(verbose, host, port, root_serve_directory, config_path, debug=False):
    app = Flask(__name__)
    app.config["ROOT_SERVE_DIRECTORY"] = root_serve_directory
    app.config["CONFIG_PATH"] = config_path
    app.register_blueprint(server)

    app.run(host=host, port=port, debug=debug)
