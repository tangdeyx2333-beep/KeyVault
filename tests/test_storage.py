import os
import tempfile
import unittest

from save_api_key.storage import ApiKeyStore


class TestApiKeyStore(unittest.TestCase):
    def test_create_list_update_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "t.db")
            store = ApiKeyStore(db_path)

            store.create("k1", "v1", "r1")
            store.create("k2", "v2", "")

            rows = store.list_all()
            self.assertEqual(
                rows,
                [
                    {"key": "k1", "value": "v1", "remark": "r1"},
                    {"key": "k2", "value": "v2", "remark": ""},
                ],
            )

            store.update("k1", "k1", "v1b", "r1b")
            rows2 = store.list_all()
            self.assertEqual(
                rows2,
                [
                    {"key": "k1", "value": "v1b", "remark": "r1b"},
                    {"key": "k2", "value": "v2", "remark": ""},
                ],
            )

            store.update("k2", "k2_new", "v2", "r2")
            rows3 = store.list_all()
            self.assertEqual(
                rows3,
                [
                    {"key": "k1", "value": "v1b", "remark": "r1b"},
                    {"key": "k2_new", "value": "v2", "remark": "r2"},
                ],
            )

            store.delete("k1")
            self.assertEqual(
                store.list_all(),
                [{"key": "k2_new", "value": "v2", "remark": "r2"}],
            )

    def test_empty_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "t.db")
            store = ApiKeyStore(db_path)
            with self.assertRaises(ValueError):
                store.create("   ", "v", "")

    def test_delete_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "t.db")
            store = ApiKeyStore(db_path)
            with self.assertRaises(KeyError):
                store.delete("missing")

    def test_update_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "t.db")
            store = ApiKeyStore(db_path)
            with self.assertRaises(KeyError):
                store.update("missing", "missing", "v", "")


if __name__ == "__main__":
    unittest.main()

