from pathlib import Path

from flask import Flask

from spendscope.db import init_db
from spendscope.routes import bp


def create_app(test_config=None):
    app = Flask(__name__, template_folder="spendscope/templates", static_folder="spendscope/static")
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        DATABASE=str(Path(app.instance_path) / "spendscope.sqlite"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)
    app.register_blueprint(bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
