from save_api_key.config import get_default_db_path
from save_api_key.storage import ApiKeyStore
from save_api_key.ui import ApiKeyApp


def main() -> None:
    store = ApiKeyStore(get_default_db_path())
    app = ApiKeyApp(store)
    app.mainloop()


if __name__ == "__main__":
    main()
