import json
import sqlite3
from pathlib import Path

from app.config.settings import data_dir_override
from app.paths import REPO_ROOT


def data_dir() -> Path:
    override = data_dir_override()
    path = Path(override) if override else REPO_ROOT / "backend" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(data_dir() / "rubbleecho.sqlite")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trials (
            trial_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    return connection


def save_trial(trial: dict) -> None:
    payload = json.dumps(trial)
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO trials (trial_id, payload) VALUES (?, ?)
            ON CONFLICT(trial_id) DO UPDATE SET payload = excluded.payload
            """,
            (trial["trial_id"], payload),
        )


def load_trial(trial_id: str) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM trials WHERE trial_id = ?",
            (trial_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
