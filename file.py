import source
from common import Stamp
from source import DAILY_STATS_FILE
# ---
from json import load, dump
from os.path import exists, getsize
from datetime import datetime
from collections import defaultdict


def SaveRequestsToFile(requests: list | dict, msg: str, file: str) -> None:
    Stamp(f'Saving {msg} requests', 'i')
    with open(file, 'w', encoding='utf-8') as f:
        dump(requests, f, ensure_ascii=False, indent=4)


def LoadRequestsFromFile(msg: str, file: str) -> list | dict:
    Stamp(f'Loading {msg} requests', 'i')
    if exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            if getsize(file) > 0:
                return load(f)
            else:
                Stamp(f'File with {msg} requests is empty', 'w')
    else:
        Stamp(f'No file with {msg} requests found', 'w')
    return []


def loadDailyStats():
    if exists(DAILY_STATS_FILE):
        try:
            with open(DAILY_STATS_FILE, 'r') as f:
                data = load(f)
                date_saved = datetime.strptime(data.get('date', ''), '%Y-%m-%d').date()
                counters = data.get('counters', {})
                return date_saved, defaultdict(int, counters)
        except:
            pass
    return datetime.now().date(), defaultdict(int)


def saveDailyStats():
    try:
        with open(DAILY_STATS_FILE, 'w') as f:
            dump({
                'date': str(source.LAST_STATS_RESET),
                'counters': dict(source.DAILY_STATS)
            }, f)
    except Exception as e:
        Stamp(f"Error saving stats: {e}", "w")


def updateDailyStats(event_type: str):
    today = datetime.now().date()
    if today != source.LAST_STATS_RESET:
        source.DAILY_STATS = defaultdict(int)
        source.LAST_STATS_RESET = today
    source.DAILY_STATS[event_type] += 1
    saveDailyStats()
