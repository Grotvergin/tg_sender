from common import Stamp
from json import load, dump
from os.path import exists, getsize


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
