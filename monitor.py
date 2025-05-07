from source import (CHECK_INTERVAL, BOT, NOTIF_TIME_DELTA, MAX_SILENCE_TIME,
                    MONITOR_TYPES, LAST_MAIN_CHECK_FILE, MAIN_PID_FILE, MAIN_SCRIPT_NAME,
                    MAIN_SCREEN_NAME, LAST_ANOMALY_CHECK_FILE, ANOMALY_PID_FILE,
                    ANOMALY_SCRIPT_NAME, ANOMALY_SCREEN_NAME, MONITOR_INTERVAL_MINS,
                    MONITOR_SILENCE_TIME)
from secret import MY_TG_ID, AR_TG_ID
from common import Stamp
# ---
from time import sleep
from json import dump, load, JSONDecodeError
from datetime import datetime, timedelta
from os import system, kill
from signal import SIGTERM
from argparse import ArgumentParser


def update_last_check(file_name):
    with open(file_name, "w") as f:
        dump({"last_check": datetime.now().isoformat()}, f)


def get_last_check(file_name):
    try:
        with open(file_name, "r") as f:
            data = load(f)
            return datetime.fromisoformat(data["last_check"])
    except (FileNotFoundError, JSONDecodeError):
        return


def find_and_kill_main(pid_file):
    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        kill(pid, SIGTERM)
        return True
    except Exception as e:
        Stamp(f'Error killing {pid_file} by PID: {e}', 'e')
        msg = f'♦ Unable to kill process {pid_file} ♦'
        BOT.send_message(MY_TG_ID, msg)
        BOT.send_message(AR_TG_ID, msg)
    return False


def monitor_bot(last_check_file, pid_file, script_name, max_timedelta):
    while True:
        sleep(CHECK_INTERVAL)
        last_check = get_last_check(last_check_file)
        if last_check and datetime.now() - last_check > timedelta(minutes=max_timedelta):
            msg = f'🟥🟥🟥🟥🟥 Error in {pid_file}, restarting 🟥🟥🟥🟥🟥'
            BOT.send_message(MY_TG_ID, msg)
            BOT.send_message(AR_TG_ID, msg)
            find_and_kill_main(pid_file)
            system(f"nohup ./{script_name} > /dev/null 2>&1 &")


if __name__ == "__main__":
    parser = ArgumentParser(description="Monitor and restart bot process if silent too long.")
    parser.add_argument("--type", required=True, help=f"Type of bot: {' or '.join(MONITOR_TYPES)}")
    args = parser.parse_args()

    if args.type == MONITOR_TYPES[0]:
        monitor_bot(
            last_check_file=LAST_MAIN_CHECK_FILE,
            pid_file=MAIN_PID_FILE,
            script_name=MAIN_SCRIPT_NAME,
            max_timedelta=NOTIF_TIME_DELTA + MAX_SILENCE_TIME
        )
    elif args.type == MONITOR_TYPES[1]:
        monitor_bot(
            last_check_file=LAST_ANOMALY_CHECK_FILE,
            pid_file=ANOMALY_PID_FILE,
            script_name=ANOMALY_SCRIPT_NAME,
            max_timedelta=MONITOR_INTERVAL_MINS + MONITOR_SILENCE_TIME
        )
    else:
        Stamp(f'Type of bot must be in {' or '.join(MONITOR_TYPES)}', 'e')
