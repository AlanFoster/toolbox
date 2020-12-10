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
import logging
import base64
from typing import Optional
from http import HTTPStatus
import netifaces

from .file_server import ServerConfig, FileServer
from .payload_generator import PayloadGenerator, TEMPLATE_DIRECTORY


server = Blueprint(
    "serve", __name__, template_folder=TEMPLATE_DIRECTORY, static_folder=None
)


class Color:
    def green(s: str) -> str:
        return f"\033[32m{s}\x1b[0m"


@server.route("/shells/<name>")
@server.route("/shells/<name>/<lport>")
@server.route("/shells/<name>/<lhost>/<lport>")
def shell(name: str, lhost: Optional[str] = None, lport: Optional[str] = None):
    payload_generator = PayloadGenerator()
    payload = payload_generator.generate(name=name, lhost=lhost, lport=lport)
    if payload is None:
        return abort(HTTPStatus.NOT_FOUND)
    response = make_response(payload)
    response.headers["Content-Type"] = "text/plain"
    return response


@server.route("/debug/", defaults={"namespace": None})
@server.route("/debug/<path:namespace>")
def debug(namespace):
    value = request.args.get("value")
    if value:
        try:
            value = base64.b32decode(value)
        except:
            value = f"Unknown base: {value}"
    current_app.logger.info(
        "debug=%s value=%s", Color.green(namespace), Color.green(value)
    )
    return make_response("", HTTPStatus.OK)


@server.route("/", defaults={"server_path": ""})
@server.route("/<path:server_path>")
def serve_file(server_path):
    payload_generator = PayloadGenerator()
    server_config = ServerConfig(
        root_directory=current_app.config["ROOT_DIRECTORY"],
        config_path=current_app.config["CONFIG_PATH"],
    )
    file_server = FileServer(
        server_config=server_config, payload_generator=payload_generator
    )

    return file_server.serve(server_path)


def serve(
    verbose,
    host,
    port,
    root_directory,
    root_serve_directory,
    config_path,
    use_debugger=False,
    use_reloader=False,
):
    app = Flask(__name__, static_folder=None)
    app.config["ROOT_DIRECTORY"] = root_directory
    app.config["ROOT_SERVE_DIRECTORY"] = root_serve_directory
    app.config["CONFIG_PATH"] = config_path
    app.config["TEMPLATES_AUTO_RELOAD"] = use_reloader

    # TODO: Add middleware logging for IP, time, user agent details, highlighting on 404s etc.
    # log = logging.getLogger("werkzeug")
    # log.disabled = True

    app.logger.setLevel(logging.INFO)
    app.register_blueprint(server)

    app.run(host=host, port=port, use_debugger=use_debugger, use_reloader=use_reloader)
