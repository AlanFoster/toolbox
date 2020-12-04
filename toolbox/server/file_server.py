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
import netifaces
import json
from pathlib import Path
from typing import List, Mapping
from .payload_generator import PayloadGenerator


ServerPath = str
LocalPath = str
ServerPathMap = Mapping[ServerPath, LocalPath]


class ServerConfig:
    def __init__(self, root_directory: str, config_path: str):
        self.root_directory = root_directory
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
            local_path = self.root_directory / local_path
            if not local_path.exists():
                raise ValueError(f"local_path '{local_path}' does not exist.")

            server_files[server_path] = Path(local_path)
        return server_files


@dataclass
class File:
    path: str
    name: str


def removeprefix(self: str, prefix: str, /) -> str:
    if self.startswith(prefix):
        return self[len(prefix) :]
    else:
        return self[:]


class FileServer:
    def __init__(
        self, server_config: ServerConfig, payload_generator: PayloadGenerator
    ):
        self.server_config = server_config
        self.payload_generator = payload_generator

    def serve(self, server_path: ServerPath):
        custom_file = self._get_custom_file(server_path)
        if custom_file is not None:
            return custom_file

        return self._get_served_file(server_path)

    def _get_served_file(self, server_path: ServerPath):
        restricted_to_path = Path(current_app.config["ROOT_SERVE_DIRECTORY"])
        root_serve_directory = Path(current_app.config["ROOT_SERVE_DIRECTORY"])
        requested_path = (root_serve_directory / server_path).resolve()

        # Ensure arbitrary file reads can't occur
        # TODO: Ensure it's a file or directory
        valid_child_path = (
            restricted_to_path in requested_path.parents
            or requested_path == restricted_to_path
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
                    path=f"/{file.relative_to(root_serve_directory).as_posix()}",
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
            valid_shell_types=self.payload_generator.template_names,
            default_lhost=self.payload_generator.default_lhost,
            default_lport=self.payload_generator.default_lport,
            files=files,
            custom_files=custom_files,
            server_path=server_path,
        )

    def _get_custom_file(self, server_path: ServerPath):
        # test instant lookup
        server_path_namespace = ""
        local_path = self.server_config.get_local_path("/" + server_path)

        # test as a namespace
        if local_path is None:
            server_path_namespace = server_path.split("/")[0]
            local_path = self.server_config.get_local_path("/" + server_path_namespace)

        if local_path is None:
            return None

        restricted_to_path = Path(local_path)

        server_path_without_namespace = removeprefix(server_path, server_path_namespace)
        if server_path_without_namespace[0] == "/":
            server_path_without_namespace = server_path_without_namespace[1:]

        # TODO: The LFI restrictions are in a different location:
        # http://localhost/static//mnt/hgfs/toolbox/static-binaries/binaries/darwin/heartbleeder
        # root_serve_directory = Path(current_app.config["ROOT_SERVE_DIRECTORY"])
        root_serve_directory = self.server_config.root_directory
        requested_path = None

        if server_path_namespace == "" or server_path_without_namespace == "/":
            requested_path = local_path
        else:
            requested_path = (
                root_serve_directory / local_path / server_path_without_namespace
            ).resolve()

        valid_child_path = (
            restricted_to_path in requested_path.parents
            or requested_path == restricted_to_path
        ) and requested_path.exists()
        if not valid_child_path:
            return abort(HTTPStatus.NOT_FOUND)

        # TODO: Ensure there's no LFI here either... Perhaps a global file read to ensure we _never_ accidentally read outside of this base toolbox.
        # TODO: Consider weird things like sockets
        if requested_path.is_file():
            with open(requested_path, "rb") as file:
                content = file.read()
                return content

            response = make_response(content)
            response.headers["Content-Type"] = "text/plain"
            return response
        elif requested_path.is_dir():
            path_prefix = None

            if server_path_namespace == "":
                path_prefix = f"/{server_path}/"
            else:
                path_prefix = f"/{server_path_namespace}/"

            files = []
            for file in requested_path.iterdir():
                files.append(
                    File(
                        path=f"{path_prefix}{str(file.relative_to(local_path).as_posix())}",
                        name=file.name,
                    )
                )
            files.sort(key=lambda file: file.name)

            return render_template(
                "index.html",
                valid_shell_types=self.payload_generator.template_names,
                default_lhost=self.payload_generator.default_lhost,
                default_lport=self.payload_generator.default_lport,
                files=files,
                custom_files=[],
                server_path=server_path,
            )
        else:
            return abort(HTTPStatus.NOT_FOUND)
