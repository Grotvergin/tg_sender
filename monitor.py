from time import sleep
from json import dump, load, JSONDecodeError
from datetime import datetime, timedelta
from source import (CHECK_INTERVAL, LAST_CHECK_FILE, BOT,
                    NOTIF_TIME_DELTA, MAX_SILENCE_TIME)
from secret import MY_TG_ID, AR_TG_ID


def update_last_check():
    with open(LAST_CHECK_FILE, "w") as f:
        dump({"last_check": datetime.now().isoformat()}, f)


def get_last_check():
    try:
        with open(LAST_CHECK_FILE, "r") as f:
            data = load(f)
            return datetime.fromisoformat(data["last_check"])
    except (FileNotFoundError, JSONDecodeError):
        return


def monitor_bot():
    while True:
        sleep(CHECK_INTERVAL)
        last_check = get_last_check()
        if last_check and datetime.now() - last_check > timedelta(minutes=NOTIF_TIME_DELTA + MAX_SILENCE_TIME):
            BOT.send_message(MY_TG_ID, '🟥🟥🟥🟥🟥 ERROR 🟥🟥🟥🟥🟥')
            BOT.send_message(AR_TG_ID, '🟥🟥🟥🟥🟥 ERROR 🟥🟥🟥🟥🟥')


if __name__ == "__main__":
    monitor_bot()
