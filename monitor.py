from source import (CHECK_INTERVAL, LAST_CHECK_FILE, BOT,
                    NOTIF_TIME_DELTA, MAX_SILENCE_TIME)
from secret import MY_TG_ID, AR_TG_ID
from common import Stamp
# ---
from time import sleep
from json import dump, load, JSONDecodeError
from datetime import datetime, timedelta
from os import system



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


def find_and_kill_main():
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        return True
    except Exception as e:
        Stamp(f'Error killing main by PID: {e}', 'e')
        msg = '♦ UNABLE TO KILL PROCESS ♦'
        BOT.send_message(MY_TG_ID, msg)
        BOT.send_message(AR_TG_ID, msg)
    return False


def restart_main():
    os.system("screen -S sender -X stuff $'./run_bot.sh\\n'")


def monitor_bot():
    while True:
        sleep(CHECK_INTERVAL)
        last_check = get_last_check()
        if last_check and datetime.now() - last_check > timedelta(minutes=NOTIF_TIME_DELTA + MAX_SILENCE_TIME):
            msg = '🟥🟥🟥🟥🟥 ERROR, KILLING AND RESTARTING 🟥🟥🟥🟥🟥'
            BOT.send_message(MY_TG_ID, msg)
            BOT.send_message(AR_TG_ID, msg)
            find_and_kill_main()
            restart_main()


if __name__ == "__main__":
    monitor_bot()
