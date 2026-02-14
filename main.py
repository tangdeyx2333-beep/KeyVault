import os
import tkinter as tk
from tkinter import ttk
from save_api_key.config import get_default_db_path
from save_api_key.storage import ApiKeyStore
from save_api_key.ui import ApiKeyApp, LoginDialog

def get_master_password() -> str | None:
    """弹出登录对话框并返回用户输入的主密码"""
    db_path = get_default_db_path()
    salt_path = db_path + ".salt"
    is_first_run = not os.path.exists(salt_path)

    print("[DEBUG] 创建Tk根窗口...")
    root = tk.Tk()
    root.title("登录 - API Key Manager")
    
    # 不再使用 withdraw()，直接让 root 充当背景或容器
    root.geometry("320x150")
    
    # 居中 root 窗口
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
    root.geometry(f"+{x}+{y}")

    print("[DEBUG] 创建 LoginDialog 对话框...")
    try:
        # 传入 is_first_run 参数
        dialog = LoginDialog(root, is_first_run=is_first_run)
        
        # 强制显示
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

        root.update()
        
    except Exception as e:
        print(f"[ERROR] 初始化对话框失败: {e}")
        root.destroy()
        return None

    print("[DEBUG] 等待登录对话框关闭...")
    root.wait_window(dialog)

    result = getattr(dialog, 'result', None)
    print(f"[DEBUG] 登录对话框已关闭，是否获得密码: {result is not None}")

    root.destroy()
    return result

def main() -> None:
    print("[DEBUG] 程序启动...")
    try:
        # 获取主密码
        print("[DEBUG] 开始获取主密码...")
        master_password = get_master_password()
        if not master_password:
            print("[DEBUG] 用户取消登录")
            return  # 用户取消
        
        print("[DEBUG] 获取到主密码，开始验证...")

        # 验证密码并创建存储
        db_path = get_default_db_path()
        store = ApiKeyStore(db_path, master_password)
        if not store.verify_password(master_password):
            # 立即置空密码变量，减少内存停留时间
            master_password = None
            # 创建临时 root 用于显示错误弹窗
            temp_root = tk.Tk()
            temp_root.withdraw()
            from tkinter import messagebox
            messagebox.showerror("登录失败", "主密码错误")
            temp_root.destroy()
            return

        print("[DEBUG] 密码验证成功，启动主应用...")
        # 验证通过后，也应尽快置空密码
        master_password = None
        
        # 启动主应用
        try:
            app = ApiKeyApp(store)
            app.mainloop()
        except ValueError as e:
            if "decryption failed" in str(e):
                from tkinter import messagebox
                messagebox.showerror(
                    "数据解密失败", 
                    "无法解密数据库内容。这通常是因为：\n"
                    "1. 输入的密码不正确\n"
                    "2. 数据库文件已损坏\n"
                    "3. 数据库使用的是旧版本的未加密格式\n\n"
                    "如果这是旧版本数据，请尝试备份并删除数据库文件后重试。"
                )
            else:
                raise e
        
    except Exception as e:
        print(f"[ERROR] 程序运行错误: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
