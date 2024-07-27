from secret import *
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from traceback import format_exc
from re import match, compile, search, MULTILINE, IGNORECASE
from threading import Thread
from googleapiclient.errors import HttpError
from ssl import SSLEOFError
from socket import gaierror
from httplib2.error import ServerNotFoundError
from googleapiclient.discovery import Resource, build
from google.oauth2.service_account import Credentials
from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, GetDialogsRequest, SendReactionRequest
from telethon.tl.types import InputPeerEmpty, Channel, ChannelForbidden, ReactionEmoji
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError, InviteRequestSentError, ReactionInvalidError
from telethon.errors.rpcerrorlist import PhoneCodeExpiredError
from telethon.events import NewMessage
from random import randint, seed, choice
from time import sleep, time
from json import load, dump
from asyncio import get_event_loop, run, create_task, sleep as async_sleep, gather, set_event_loop, new_event_loop
from os.path import exists, join, getsize
from os import getcwd
from socks import SOCKS5
import emoji as lib_emoji
from requests import get, Session
from typing import Union, Callable, Any, List, Dict, Generator
from functools import wraps


BOT = TeleBot(TOKEN)
WELCOME_BTNS = ('Разовые заявки 1️⃣',
                'Автоматические заявки ⏳',
                'Авторизация аккаунтов 🔐',
                'Активные аккаунты 🦾',
                'Покупка аккаунтов 💰')
CANCEL_BTN = ('В меню ↩️',)
AUTO_CHOICE = ('Просмотры 👀', 'Репосты 📢', CANCEL_BTN[0])
AUTO_BTNS = ('Добавление 📌', 'Удаление ❌', 'Активные 📅', CANCEL_BTN[0])
SINGLE_BTNS = ('Активные 📅', 'Выполненные заявки 📋', 'Подписки 🔔', 'Просмотры 👀', 'Репосты 📢', 'Удаление ❌', 'Реакции 😍', CANCEL_BTN[0])
REQS_QUEUE = []
ACCOUNTS = []
FINISHED_REQS = []
CUR_REQ = {}
AUTO_SUBS_DICT = {}
AUTO_REPS_DICT = {}
CODE = None
init()
seed()
CREDS = Credentials.from_service_account_file('keys.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
LONG_SLEEP = 15
SHORT_SLEEP = 1
LINK_FORMAT = r'https://t\.me/'
MAX_MINS = 300
TIME_FORMAT = '%Y-%m-%d %H:%M'
ADMIN_CHAT_ID = MY_TG_ID
MAX_WAIT_CODE = 180
LINK_DECREASE_RATIO = 3
LIMIT_DIALOGS = 1000
MAX_MINS_REQ = 20
SHEET_NAME = 'Тестирование'
MAX_ACCOUNTS_BUY = 10
URL_BUY = 'https://onlinesim.io/api/getNum.php'
URL_SMS = 'https://onlinesim.io/api/getState.php'
URL_API_GET_CODE = 'https://my.telegram.org/auth/send_password'
URL_API_LOGIN = 'https://my.telegram.org/auth/login'
URL_API_GET_APP = 'https://my.telegram.org/apps'
MAX_RECURSION = 10
NUMBER_LAST_FIN = 10
LEFT_CORNER = 'A2'
RIGHT_CORNER = 'H500'
CONN_ERRORS = (TimeoutError, ServerNotFoundError, gaierror, HttpError, SSLEOFError)

HEADERS = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'ru-RU,ru;q=0.6',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://my.telegram.org',
    'priority': 'u=1, i',
    'referer': 'https://my.telegram.org/auth',
    'sec-ch-ua': '"Not)A;Brand";v="99", "Brave";v="127", "Chromium";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': None,
    'x-requested-with': 'XMLHttpRequest',
}


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]


class SkippedCodeInsertion(Exception):
    pass


def ControlRecursion(func: Callable[..., Any], maximum: int = MAX_RECURSION) -> Callable[..., Any]:
    func.recursion_depth = 0

    @wraps(func)
    def Wrapper(*args, **kwargs):
        if func.recursion_depth > maximum:
            Stamp('Max level of recursion reached', 'e')
            raise RecursionError
        if func.recursion_depth > 0:
            Stamp(f"Recursion = {func.recursion_depth}, allowed = {maximum}", 'w')
        func.recursion_depth += 1
        result = func(*args, **kwargs)
        func.recursion_depth -= 1
        return result
    return Wrapper


@ControlRecursion
def UploadData(list_of_rows: list, sheet_name: str, sheet_id: str, service: Resource, row: int = 2) -> None:
    Stamp(f'Trying to upload data to sheet {sheet_name}', 'i')
    try:
        width = len(list_of_rows[0])
    except IndexError:
        width = 0
    try:
        res = service.spreadsheets().values().update(spreadsheetId=sheet_id,
                                                     range=f'{sheet_name}!A{row}:{MakeColumnIndexes()[width]}{row + len(list_of_rows)}',
                                                     valueInputOption='USER_ENTERED',
                                                     body={'values': list_of_rows}).execute()
    except CONN_ERRORS as err:
        Stamp(f'Status = {err} on uploading data to sheet {sheet_name}', 'e')
        Sleep(LONG_SLEEP)
        UploadData(list_of_rows, sheet_name, sheet_id, service, row)
    else:
        Stamp(f"On uploading: {res.get('updatedRows')} rows in range {res.get('updatedRange')}", 's')


def MakeColumnIndexes() -> dict:
    indexes = {}
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for i, letter in enumerate(alphabet):
        indexes[i] = letter
    for i in range(len(alphabet)):
        for j in range(len(alphabet)):
            indexes[len(alphabet) + i * len(alphabet) + j] = alphabet[i] + alphabet[j]
    return indexes


def Stamp(message: str, level: str) -> None:
    time_stamp = datetime.now().strftime('[%m-%d|%H:%M:%S]')
    match level:
        case 'i':
            print(Fore.LIGHTBLUE_EX + time_stamp + '[INF] ' + message + '.' + Style.RESET_ALL)
        case 'w':
            print(Fore.LIGHTMAGENTA_EX + time_stamp + '[WAR] ' + message + '!' + Style.RESET_ALL)
        case 's':
            print(Fore.LIGHTGREEN_EX + time_stamp + '[SUC] ' + message + '.' + Style.RESET_ALL)
        case 'e':
            print(Fore.RED + time_stamp + '[ERR] ' + message + '!!!' + Style.RESET_ALL)
        case 'l':
            print(Fore.WHITE + time_stamp + '[SLE] ' + message + '...' + Style.RESET_ALL)
        case 'b':
            print(Fore.LIGHTYELLOW_EX + time_stamp + '[BOR] ' + message + '.' + Style.RESET_ALL)
        case _:
            print(Fore.WHITE + time_stamp + '[UNK] ' + message + '?' + Style.RESET_ALL)


def BuildService() -> Resource:
    Stamp(f'Trying to build service', 'i')
    try:
        service = build('sheets', 'v4', credentials=CREDS)
    except (HttpError, TimeoutError, ServerNotFoundError, gaierror, SSLEOFError) as err:
        Stamp(f'Status = {err} on building service', 'e')
        Sleep(LONG_SLEEP)
        BuildService()
    else:
        Stamp('Built service successfully', 's')
        return service


def ShowButtons(message: Message | int, buttons: tuple, answer: str) -> None:
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    if type(message) == Message:
        user_id = message.from_user.id
    else:
        user_id = message
    if len(buttons) % 2 == 0:
        for i in range(0, len(buttons), 2):
            row_buttons = buttons[i:i + 2]
            markup.row(*[KeyboardButton(btn) for btn in row_buttons])
    else:
        for i in range(0, len(buttons) - 1, 2):
            row_buttons = buttons[i:i + 2]
            markup.row(*[KeyboardButton(btn) for btn in row_buttons])
        markup.row(KeyboardButton(buttons[-1]))
    BOT.send_message(user_id, answer, reply_markup=markup)


def GetSector(start: str, finish: str, service: Resource, sheet_name: str, sheet_id: str) -> list:
    Stamp(f'Trying to get sector from {start} to {finish} from sheet {sheet_name}', 'i')
    try:
        res = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f'{sheet_name}!{start}:{finish}').execute().get('values', [])
    except (TimeoutError, ServerNotFoundError, gaierror, HttpError, SSLEOFError) as err:
        Stamp(f'Status = {err} on getting sector from {start} to {finish} from sheet {sheet_name}', 'e')
        Sleep(LONG_SLEEP)
        res = GetSector(start, finish, service, sheet_name, sheet_id)
    else:
        if not res:
            Stamp(f'No elements in sector from {start} to {finish} sheet {sheet_name} found', 'w')
        else:
            Stamp(f'Found {len(res)} rows from sector from {start} to {finish} sheet {sheet_name}', 's')
    return res


def Sleep(timer: int, ratio: float = 0.0) -> None:
    rand_time = randint(int((1 - ratio) * timer), int((1 + ratio) * timer))
    Stamp(f'Sleeping {rand_time} seconds', 'l')
    sleep(rand_time)


async def AsyncSleep(timer: int, ratio: float = 0.0) -> None:
    rand_time = randint(int((1 - ratio) * timer), int((1 + ratio) * timer))
    Stamp(f'Sleeping asynchronously {rand_time} seconds', 'l')
    await async_sleep(rand_time)
