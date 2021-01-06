import pytest
from toolbox.server import server
from pathlib import Path
from flask import Flask
from http import HTTPStatus
import secrets
from flask_wtf.csrf import CSRFError, CSRFProtect, CsrfProtect, generate_csrf


# Open the given response in a browser to inspect the rendered html
@pytest.fixture
def open_response():
    def _open_response(response):
        import tempfile
        import subprocess
        import time

        with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
            tmp.write(response.data)
            tmp.flush()
            subprocess.run(["open", tmp.name])
            time.sleep(1)

    return _open_response


@pytest.fixture
def app():
    app = Flask(__name__)
    test_harness = Path(__file__).parent / "harnesses" / "simple"
    app.config["ROOT_USER_DIRECTORY"] = test_harness / "serve"
    app.config["ROOT_TOOLBOX_DIRECTORY"] = test_harness / "toolbox"
    app.config["CONFIG_PATH"] = test_harness / "toolbox" / "config.json"
    app.register_blueprint(server.server)

    secret_key = secrets.token_bytes(32)
    app.secret_key = secret_key
    server.csrf.init_app(app)

    @app.route("/csrf_token", methods=["GET"])
    def csrf_token():
        return generate_csrf()

    return app


@pytest.fixture
def req_ctx(app):
    with app.test_request_context() as ctx:
        yield ctx


@pytest.fixture
def client(app):
    return app.test_client()
