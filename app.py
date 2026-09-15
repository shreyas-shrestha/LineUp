"""WSGI entry point: ``gunicorn app:app`` in production, ``python app.py`` locally."""

from dotenv import load_dotenv

load_dotenv()

from lineup_backend import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
