# 🛡️ SECURITY AUDIT REPORT (代码安全审计报告)

## 1. 审计概览 (Executive Summary)
* **审计对象**: `main.py`, `storage.py`, `ui.py` (API Key Manager Core)
* **整体安全评分**: 95/100
* **威胁等级**: 🔵 低 / Low
* **一句话结论**: Cerberus 确认：核心加固已完成。系统已从之前的“漏洞地狱”进化为具备生产级防御能力的堡垒。当前仅存少量架构性防御建议。

## 2. 漏洞矩阵 (Vulnerability Matrix)
| ID | 漏洞类型 (CWE) | 严重程度 | 位置 (行号) | 简述 |
|----|---------------|---------|------------|------|
| V1 | Insecure Storage | 🔵 Low | `storage.py:L29, L46` | Salt 和 Verifier 作为独立文件存储，易被意外删除 |
| V2 | Memory Safety | 🔵 Low | `ui.py:L61, L65` | 主密码在内存中以普通字符串形式存在，无法被及时置零 |

## 3. 深度分析与漏洞复现 (Detailed Analysis)

### [V1] 🔵 Low: Sensitive Metadata Fragmentation
* **原理分析**: 系统将 `salt` 和 `verifier` 存储在与数据库并列的 `.salt` 和 `.verifier` 文件中。虽然这在逻辑上是安全的，但增加了文件系统的攻击面。如果用户备份了 `.db` 却遗漏了这两个隐藏文件，数据将永久锁定。
* **致命后果**: 导致合法的用户数据丢失（Denial of Service to self），或在多用户环境下被定向删除导致认证失效。
* **代码证据**:
    ```python
    # storage.py
    salt_path = self._db_path + ".salt"
    verifier_path = self._db_path + ".verifier"
    ```

### [V2] 🔵 Low: Plaintext Credentials in Memory
* **原理分析**: Python 的字符串（`str`）是不可变的。当用户在 `LoginDialog` 输入密码时，密码会作为字符串驻留在内存中。即使 `LoginDialog` 被销毁，垃圾回收器（GC）也不一定会立即擦除这块内存。
* **攻击向量**: 本地拥有高级权限的攻击者通过内存 dump（如使用 `WinDbg` 或 `Volatility`）可能提取到残留的主密码字符串。
* **致命后果**: 主密码泄露，导致整个密钥库失守。
* **代码证据**:
    ```python
    # ui.py
    self.result = pwd # 引用了 Entry 获取的原始字符串
    ```

## 4. 修复方案 (Remediation)

### Fix for [V1]: 整合存储 (Architecture Hardening)
* **修复策略**: 将 Salt 和 Verifier 存储在 SQLite 内部的一个元数据表（`metadata`）中，确保“库在人在，库亡人亡”。
* **安全建议代码**:
    ```python
    # 在 _init_db 中增加
    conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value BLOB)")
    ```

### Fix for [V2]: 内存保护 (Defense in Depth)
* **修复策略**: 虽然 Python 难以完全避免内存残留，但可以在主流程中尽可能减少密码字符串的生命周期。建议在验证完成后，将 `master_password` 变量设为 `None`。
* **安全代码**:
    ```python
    # main.py
    master_password = get_master_password()
    store = ApiKeyStore(db_path, master_password)
    # ... 验证通过后 ...
    master_password = None # 尽早解除引用
    ```

## 5. 潜在风险与架构建议 (Subtle Risks)
* **[Recommendation 1] 剪贴板二次加固**: 目前 30 秒自动清除已实现。建议增加应用关闭时强制清除剪贴板的逻辑，防止用户复制后直接关闭程序。
* **[Recommendation 2] 数据库锁定**: 建议对 `apikeys.db` 文件设置文件系统级的锁定（Locking），防止多个实例同时写入导致加密块损坏。
* **[Recommendation 3] 异常回退安全**: 在 `storage.py` 的 `_decrypt` 中，虽然增加了对旧数据的兼容，但建议在迁移完成后，在日志中明确提示用户旧数据已加固，并建议删除可能存在的明文备份。
