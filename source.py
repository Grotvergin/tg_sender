from secret import *
import telebot
from colorama import Fore, Style, init
from datetime import datetime, timedelta, date
import traceback
import re
from typing import Dict, Any
from threading import Thread, Event
from socket import gaierror
from ssl import SSLEOFError
from googleapiclient.errors import HttpError
import googleapiclient.discovery
import httplib2
import time
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
import socket
import ssl
from telethon.sync import TelegramClient
import os
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
import asyncio


SLEEP_GOOGLE = 20
BOT = telebot.TeleBot(TOKEN)
WELCOME_BTNS = ('Подписаться на канал 🔔', 'Увеличить просмотры поста 📈', 'Активные заявки 📅')
REQS_QUEUE = []
CUR_REQ = {}
ACCOUNTS = []
init()
random.seed()
CREDS = service_account.Credentials.from_service_account_file('keys.json', scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly'])
CUR_ACC_INDEX = 0
LONG_SLEEP = 15
SHORT_SLEEP = 2


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


def BuildService() -> googleapiclient.discovery.Resource:
    Stamp(f'Trying to build service', 'i')
    try:
        service = build('sheets', 'v4', credentials=CREDS)
    except (HttpError, TimeoutError, httplib2.error.ServerNotFoundError, socket.gaierror, ssl.SSLEOFError) as err:
        Stamp(f'Status = {err} on building service', 'e')
        Sleep(SLEEP_GOOGLE)
        BuildService()
    else:
        Stamp('Built service successfully', 's')
        return service


service = BuildService()


def ShowButtons(message: telebot.types.Message, buttons: tuple, answer: str) -> None:
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for btn in buttons:
        markup.row(telebot.types.KeyboardButton(btn))
    BOT.send_message(message.from_user.id, answer, reply_markup=markup)


def GetSector(start: str, finish: str, service: googleapiclient.discovery.Resource, sheet_name: str, sheet_id: str) -> list:
    Stamp(f'Trying to get sector from {start} to {finish} from sheet {sheet_name}', 'i')
    try:
        res = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f'{sheet_name}!{start}:{finish}').execute().get('values', [])
    except (TimeoutError, httplib2.error.ServerNotFoundError, gaierror, HttpError, SSLEOFError) as err:
        Stamp(f'Status = {err} on getting sector from {start} to {finish} from sheet {sheet_name}', 'e')
        Sleep(SLEEP_GOOGLE)
        res = GetSector(start, finish, service, sheet_name, sheet_id)
    else:
        if not res:
            Stamp(f'No elements in sector from {start} to {finish} sheet {sheet_name} found', 'w')
        else:
            Stamp(f'Found {len(res)} rows from sector from {start} to {finish} sheet {sheet_name}', 's')
    return res


def Sleep(timer: int, ratio: float = 0.0) -> None:
    rand_time = random.randint(int((1 - ratio) * timer), int((1 + ratio) * timer))
    Stamp(f'Sleeping {rand_time} seconds', 'l')
    time.sleep(rand_time)