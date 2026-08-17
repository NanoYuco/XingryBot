import logging

from bot.application import build_application
from database import init_db


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    init_db()
    app = build_application()

    print("喵喵已就位！")
    app.run_polling()


if __name__ == "__main__":
    main()
