from secret import *
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from traceback import format_exc
from re import match, compile
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
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel, ChannelForbidden
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.errors.rpcerrorlist import PhoneCodeExpiredError
from telethon.events import NewMessage
from random import randint, seed
from time import sleep, time
from json import load, dump
from asyncio import get_event_loop, run, create_task, sleep as async_sleep, gather, run_coroutine_threadsafe, set_event_loop, new_event_loop
from os.path import exists, join, getsize
from os import getcwd, listdir, walk


BOT = TeleBot(TOKEN)
WELCOME_BTNS = ('Разовые заявки 1️⃣',
                'Автоматические заявки ⏳',
                'Авторизация аккаунтов 🔐')
CANCEL_BTN = ('В меню ↩️',)
AUTO_CHOICE = ('Просмотры 👀', 'Репосты 📢', CANCEL_BTN[0])
AUTO_BTNS = ('Добавление 📌', 'Удаление ❌', 'Активные 📅', CANCEL_BTN[0])
SINGLE_BTNS = ('Активные 📅', 'Выполненные заявки 📋', 'Подписки 🔔', 'Просмотры 👀', 'Репосты 📢', CANCEL_BTN[0])
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
CUR_ACC_INDEX = 0
LONG_SLEEP = 15
SHORT_SLEEP = 1
LINK_FORMAT = r'https://t\.me/'
MAX_MINS = 300
TIME_FORMAT = '%Y-%m-%d %H:%M'
ADMIN_CHAT_ID = 386988582
MAX_WAIT_CODE = 120
LINK_DECREASE_RATIO = 3


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