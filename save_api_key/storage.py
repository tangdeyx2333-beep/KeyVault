import os
import sqlite3
import base64
from contextlib import contextmanager
from typing import Iterator, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ApiKeyRecord:
    def __init__(self, key: str, value: str, remark: str) -> None:
        self.key = key
        self.value = value
        self.remark = remark


class ApiKeyStore:
    def __init__(self, db_path: str, master_password: str | None = None) -> None:
        self._db_path = db_path
        self._cipher: Fernet | None = None
        self._salt: bytes | None = None
        self._verifier: bytes | None = None
        if master_password is not None:
            self._derive_key(master_password)
        self._init_db()

    def _derive_key(self, master_password: str) -> None:
        salt_path = self._db_path + ".salt"
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                self._salt = f.read()
        else:
            self._salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(self._salt)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self._cipher = Fernet(key)
        self._verifier = self._cipher.encrypt(b"VERIFIER")
        verifier_path = self._db_path + ".verifier"
        with open(verifier_path, "wb") as f:
            f.write(self._verifier)

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

    def _normalize_str(self, s: str) -> str:
        s = s.strip()
        if not s:
            raise ValueError("string must be non-empty")
        return s

    def _normalize_key(self, key: str) -> str:
        key_str = self._normalize_str(key)
        if len(key_str) > 100:
            raise ValueError("key too long (max 100)")
        return key_str

    def _normalize_value(self, value: str) -> str:
        val = self._normalize_str(value)
        if len(val) > 2000:
            raise ValueError("value too long (max 2000)")
        return val

    def _normalize_remark(self, remark: str) -> str:
        rem = self._normalize_str(remark)
        if len(rem) > 500:
            raise ValueError("remark too long (max 500)")
        return rem

    def _encrypt(self, plaintext: str) -> str:
        if not self._cipher:
            raise RuntimeError("encryption key not set")
        # Fernet.encrypt 返回的就是 base64 编码的 bytes
        return self._cipher.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        if not self._cipher:
            raise RuntimeError("encryption key not set")
        
        # 兼容性逻辑：如果 ciphertext 看起来不像 Fernet 密文（通常以 gAAAA... 开头）
        # 或者解密失败，我们尝试判断它是否是旧版本的明文数据
        if not ciphertext.startswith("gAAAA"):
            # 这里的判断标准是：如果它不符合 Fernet 格式，且不是空字符串，我们暂且认为它是旧数据
            # 真正的解密动作在 try 块中
            pass

        try:
            # Fernet.decrypt 接受 base64 编码的 bytes 或 str
            plaintext = self._cipher.decrypt(ciphertext.encode())
            return plaintext.decode()
        except (InvalidToken, base64.binascii.Error, ValueError):
            # 如果解密失败，且数据不符合 Fernet 密文特征，尝试直接返回原文（旧版本明文）
            # 注意：这只会在用户输入了正确的主密码但数据库里混有旧数据时发生
            print(f"[DEBUG] 解密失败，尝试作为明文返回: {ciphertext[:10]}...")
            return ciphertext

    def verify_password(self, master_password: str) -> bool:
        try:
            salt_path = self._db_path + ".salt"
            verifier_path = self._db_path + ".verifier"
            if not os.path.exists(salt_path) or not os.path.exists(verifier_path):
                return True
            with open(salt_path, "rb") as f:
                self._salt = f.read()
            with open(verifier_path, "rb") as f:
                verifier = f.read()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            cipher = Fernet(key)
            try:
                decrypted = cipher.decrypt(verifier)
                return decrypted == b"VERIFIER"
            except InvalidToken:
                return False
        except Exception:
            return False

    def list_all(self) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value, remark FROM apikeys ORDER BY key ASC"
            ).fetchall()
        
        decrypted_rows = []
        needs_migration = False
        
        for row in rows:
            raw_value = row["value"]
            try:
                # 尝试解密
                decrypted_value = self._decrypt(raw_value)
                # 如果解密出的结果和原值一样，且原值不符合密文特征，说明是旧数据
                if decrypted_value == raw_value and not raw_value.startswith("gAAAA"):
                    needs_migration = True
            except Exception:
                decrypted_value = raw_value
                needs_migration = True

            decrypted_rows.append({
                "key": row["key"],
                "value": decrypted_value,
                "remark": row["remark"],
            })
        
        # 如果发现旧数据，自动进行迁移（重新加密存储）
        if needs_migration:
            print("[INFO] 检测到旧版本明文数据，正在自动迁移加密...")
            self._migrate_to_encrypted(decrypted_rows)
            
        return decrypted_rows

    def _migrate_to_encrypted(self, decrypted_data: list[dict[str, str]]):
        """将明文数据重新加密并存回数据库"""
        with self._connect() as conn:
            for item in decrypted_data:
                encrypted_value = self._encrypt(item["value"])
                conn.execute(
                    "UPDATE apikeys SET value = ? WHERE key = ?",
                    (encrypted_value, item["key"])
                )
            conn.commit()
        print("[INFO] 数据库迁移完成")

    def create(self, key: str, value: str, remark: str) -> ApiKeyRecord:
        key_n = self._normalize_key(key)
        value_n = self._normalize_value(value)
        remark_n = self._normalize_remark(remark)
        encrypted_value = self._encrypt(value_n)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO apikeys (key, value, remark) VALUES (?, ?, ?)",
                (key_n, encrypted_value, remark_n),
            )
            conn.commit()
        return ApiKeyRecord(key_n, value_n, remark_n)

    def get(self, key: str) -> Optional[ApiKeyRecord]:
        key_n = self._normalize_key(key)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT key, value, remark FROM apikeys WHERE key = ?", (key_n,)
            ).fetchone()
        if not row:
            return None
        decrypted_value = self._decrypt(row["value"])
        return ApiKeyRecord(row["key"], decrypted_value, row["remark"])

    def update(self, old_key: str, new_key: str, new_value: str, new_remark: str) -> ApiKeyRecord:
        old_key_n = self._normalize_key(old_key)
        new_key_n = self._normalize_key(new_key)
        new_value_n = self._normalize_value(new_value)
        new_remark_n = self._normalize_remark(new_remark)
        encrypted_new_value = self._encrypt(new_value_n)
        with self._connect() as conn:
            conn.execute(
                "UPDATE apikeys SET key = ?, value = ?, remark = ? WHERE key = ?",
                (new_key_n, encrypted_new_value, new_remark_n, old_key_n),
            )
            conn.commit()
        return ApiKeyRecord(new_key_n, new_value_n, new_remark_n)

    def delete(self, key: str) -> None:
        key_n = self._normalize_key(key)
        with self._connect() as conn:
            conn.execute("DELETE FROM apikeys WHERE key = ?", (key_n,))
            conn.commit()
