import os
import tempfile
import unittest
from save_api_key.storage import ApiKeyStore


class TestSecureStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.master_password = "StrongPassword123!"
        self.store = ApiKeyStore(self.db_path, self.master_password)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        salt_path = self.db_path + ".salt"
        if os.path.exists(salt_path):
            os.remove(salt_path)
        verifier_path = self.db_path + ".verifier"
        if os.path.exists(verifier_path):
            os.remove(verifier_path)
        os.rmdir(self.tmpdir)

    def test_create_and_list(self) -> None:
        record = self.store.create("test_key", "test_value", "test_remark")
        self.assertEqual(record.key, "test_key")
        self.assertEqual(record.value, "test_value")
        self.assertEqual(record.remark, "test_remark")

        rows = self.store.list_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "test_key")
        self.assertEqual(rows[0]["value"], "test_value")
        self.assertEqual(rows[0]["remark"], "test_remark")

    def test_update(self) -> None:
        self.store.create("old_key", "old_value", "old_remark")
        updated = self.store.update("old_key", "new_key", "new_value", "new_remark")
        self.assertEqual(updated.key, "new_key")
        self.assertEqual(updated.value, "new_value")
        self.assertEqual(updated.remark, "new_remark")

        rows = self.store.list_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "new_key")

    def test_delete(self) -> None:
        self.store.create("del_key", "del_value", "del_remark")
        self.store.delete("del_key")
        rows = self.store.list_all()
        self.assertEqual(len(rows), 0)

    def test_verify_password(self) -> None:
        self.assertTrue(self.store.verify_password(self.master_password))
        self.assertFalse(self.store.verify_password("WrongPassword"))

    def test_verify_password_after_restart(self) -> None:
        self.store.create("key", "value", "remark")
        new_store = ApiKeyStore(self.db_path, self.master_password)
        self.assertTrue(new_store.verify_password(self.master_password))
        self.assertFalse(new_store.verify_password("WrongPassword"))

    def test_encryption(self) -> None:
        self.store.create("enc_key", "secret_value", "enc_remark")
        with open(self.db_path, "rb") as f:
            raw = f.read()
        self.assertNotIn(b"secret_value", raw)

    def test_input_validation(self) -> None:
        with self.assertRaises(ValueError):
            self.store.create("", "value", "remark")
        with self.assertRaises(ValueError):
            self.store.create("k" * 101, "value", "remark")
        with self.assertRaises(ValueError):
            self.store.create("key", "v" * 2001, "remark")
        with self.assertRaises(ValueError):
            self.store.create("key", "value", "r" * 501)

    def test_verify_password_empty_db(self) -> None:
        empty_db_path = os.path.join(self.tmpdir, "empty.db")
        empty_store = ApiKeyStore(empty_db_path, "AnyPassword")
        self.assertTrue(empty_store.verify_password("AnyPassword"))
        if os.path.exists(empty_db_path):
            os.remove(empty_db_path)
        salt_path = empty_db_path + ".salt"
        if os.path.exists(salt_path):
            os.remove(salt_path)
        verifier_path = empty_db_path + ".verifier"
        if os.path.exists(verifier_path):
            os.remove(verifier_path)


if __name__ == "__main__":
    unittest.main()
