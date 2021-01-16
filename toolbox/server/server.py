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
    session,
)
import logging
import base64
from typing import Optional
from http import HTTPStatus
import netifaces
from flask_wtf.csrf import CSRFProtect
from .file_server import (
    ServerConfig,
    FileServer,
    FileManager,
    ServerInvalidFilePath,
    ServerDirectoryListing,
    ServerFileResult,
)
from . import formatters
from .payload_generator import PayloadGenerator, TEMPLATE_DIRECTORY
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
from pathlib import Path
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from dataclasses import dataclass
from typing import Dict
import secrets
from http import HTTPStatus


class UploadForm(FlaskForm):
    token_id = StringField("token", validators=[DataRequired()])
    file = FileField(validators=[FileRequired()])


class UploadTokenForm(FlaskForm):
    file_name = StringField("File Name", validators=[DataRequired()])


UploadTokenId = str


@dataclass
class UploadToken:
    id: UploadTokenId
    file_name: str


@dataclass
class IndexViewModel:
    payload_generator: PayloadGenerator
    directory_listing: ServerDirectoryListing
    upload_token_form: UploadForm
    upload_token: UploadToken


upload_tokens: Dict[UploadTokenId, UploadToken] = {}


class Color:
    @classmethod
    def green(self, s: str) -> str:
        return f"\033[32m{s}\x1b[0m"


server = Blueprint(
    "serve", __name__, template_folder=TEMPLATE_DIRECTORY, static_folder=None
)
server.app_template_filter("pretty_date")(formatters.pretty_date)

csrf = CSRFProtect()


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
            value = base64.b64decode(value)
        except:
            value = f"Unknown base: {value}"
    current_app.logger.info(
        "debug=%s value=%s", Color.green(namespace), Color.green(value)
    )
    return make_response("", HTTPStatus.OK)


@server.route("/uploads", methods=["POST"])
@csrf.exempt
def uploads():
    upload_form = UploadForm(meta={"csrf": False})
    if upload_form.validate_on_submit():
        upload_token_id = upload_form.token_id.data
        upload_token = upload_tokens.get(upload_token_id, None)

        if upload_token is None:
            return make_response(
                '{ "error": "token not valid" }\n', HTTPStatus.BAD_REQUEST
            )

        file_manager = FileManager(
            root_user_directory=current_app.config["ROOT_USER_DIRECTORY"],
            root_toolbox_directory=current_app.config["ROOT_TOOLBOX_DIRECTORY"],
        )

        file = upload_form.file.data
        file_name = upload_token.file_name
        new_file_path = Path(current_app.config["ROOT_USER_DIRECTORY"]) / file_name

        if not file_manager.is_allowed_user_file_path(new_file_path):
            return make_response(
                '{ "error": "invalid path" }\n', HTTPStatus.BAD_REQUEST
            )

        with file_manager.open_user_file(new_file_path, "wb") as new_file:
            current_app.logger.info(
                "Successfully wrote new file %s", Color.green(new_file_path)
            )
            new_file.write(file.read())

        upload_tokens.pop(upload_token_id, None)
        return make_response('{ "success": true }\n', HTTPStatus.CREATED)

    return make_response(upload_form.errors, HTTPStatus.BAD_REQUEST)


@server.route("/", defaults={"server_path": ""}, methods=["GET", "POST"])
@server.route("/<path:server_path>", methods=["GET", "POST"])
def index(server_path):
    payload_generator = PayloadGenerator()
    file_manager = FileManager(
        root_user_directory=current_app.config["ROOT_USER_DIRECTORY"],
        root_toolbox_directory=current_app.config["ROOT_TOOLBOX_DIRECTORY"],
    )
    server_config = ServerConfig(
        root_toolbox_directory=current_app.config["ROOT_TOOLBOX_DIRECTORY"],
        #  TODO: Remove config path and assume only built in files can be mapped
        config_path=current_app.config["CONFIG_PATH"],
        file_manager=file_manager,
    )
    file_server = FileServer(server_config=server_config)
    server_response = file_server.serve(server_path)

    if isinstance(server_response, ServerInvalidFilePath):
        return abort(HTTPStatus.NOT_FOUND)

    if isinstance(server_response, ServerFileResult):
        response = make_response(server_response.content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    if isinstance(server_response, ServerDirectoryListing):
        form = UploadTokenForm()
        upload_token = None
        if form.validate_on_submit():
            upload_token = UploadToken(
                id=secrets.token_hex(16),
                file_name=form.file_name.data,
            )
            upload_tokens[upload_token.id] = upload_token

        return render_template(
            "views/index.html",
            view_model=IndexViewModel(
                payload_generator=payload_generator,
                directory_listing=server_response,
                upload_token_form=UploadTokenForm(),
                upload_token=upload_token,
            ),
        )

    return abort(HTTPStatus.INTERNAL_SERVER_ERROR, f"{str(server_response.__class__)}")


def serve(
    verbose,
    host,
    port,
    root_toolbox_directory,
    root_user_directory,
    config_path,
    use_debugger=False,
    use_reloader=False,
):
    app = Flask(
        __name__,
        static_url_path="/assets",
        static_folder=str(root_toolbox_directory / "toolbox" / "server" / "assets"),
    )
    app.config["ROOT_TOOLBOX_DIRECTORY"] = root_toolbox_directory
    app.config["ROOT_USER_DIRECTORY"] = root_user_directory
    app.config["CONFIG_PATH"] = config_path
    app.config["TEMPLATES_AUTO_RELOAD"] = use_reloader
    secret_key = secrets.token_bytes(32)
    app.secret_key = secret_key
    csrf.init_app(app)

    # TODO: Add middleware logging for IP, time, user agent details, highlighting on 404s etc.
    # log = logging.getLogger("werkzeug")
    # log.disabled = True

    app.logger.setLevel(logging.INFO)
    app.register_blueprint(server)

    app.run(host=host, port=port, use_debugger=use_debugger, use_reloader=use_reloader)
