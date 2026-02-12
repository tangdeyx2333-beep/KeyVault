from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    key: str
    value: str
    remark: str


class ApiKeyStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS apikeys (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    remark TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _normalize_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("value must be str")

    @classmethod
    def _normalize_key(cls, key: Any) -> str:
        key_str = cls._normalize_str(key).strip()
        if not key_str:
            raise ValueError("key must be non-empty")
        return key_str

    @classmethod
    def _normalize_value(cls, value: Any) -> str:
        return cls._normalize_str(value)

    @classmethod
    def _normalize_remark(cls, remark: Any) -> str:
        return cls._normalize_str(remark)

    def list_all(self) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value, remark FROM apikeys ORDER BY key ASC"
            ).fetchall()
        return [
            {"key": row["key"], "value": row["value"], "remark": row["remark"]}
            for row in rows
        ]

    def create(self, key: Any, value: Any, remark: Any) -> ApiKeyRecord:
        key_n = self._normalize_key(key)
        value_n = self._normalize_value(value)
        remark_n = self._normalize_remark(remark)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO apikeys(key, value, remark) VALUES (?, ?, ?)",
                (key_n, value_n, remark_n),
            )
            conn.commit()
        return ApiKeyRecord(key=key_n, value=value_n, remark=remark_n)

    def update(
        self, old_key: Any, new_key: Any, value: Any, remark: Any
    ) -> ApiKeyRecord:
        old_key_n = self._normalize_key(old_key)
        new_key_n = self._normalize_key(new_key)
        value_n = self._normalize_value(value)
        remark_n = self._normalize_remark(remark)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE apikeys SET key = ?, value = ?, remark = ? WHERE key = ?",
                (new_key_n, value_n, remark_n, old_key_n),
            )
            if cur.rowcount != 1:
                raise KeyError(old_key_n)
            conn.commit()
        return ApiKeyRecord(key=new_key_n, value=value_n, remark=remark_n)

    def delete(self, key: Any) -> None:
        key_n = self._normalize_key(key)
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM apikeys WHERE key = ?", (key_n,))
            if cur.rowcount != 1:
                raise KeyError(key_n)
            conn.commit()
