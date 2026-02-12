from __future__ import annotations

import os


def get_default_db_path() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".save_api_key")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "apikeys.db")

