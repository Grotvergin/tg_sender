from telebot import TeleBot
from secret import TOKEN, MY_TG_ID, TOKEN_TEST
from colorama import init
from faker import Faker
from random import seed
from googleapiclient.errors import HttpError
from httplib2.error import ServerNotFoundError
from ssl import SSLEOFError
from socket import gaierror
from datetime import datetime

# ----- TODO LIST -----
# Button for returning the request + fast channelname copying ability
# Showing a list of auto reqs like single ones
# Truncate amount of data in error message from appium
# Buying more than one account test
# External smartphone connection


WELCOME_BTNS = ('Разовые 1️⃣',
                'Автоматические ⏳',
                'Авторизация 🔐',
                'Активные 🦾',
                'Покупка 💰',
                'Изменение 🔄',)
CANCEL_BTN = ('Меню ↩️',)
AUTO_CHOICE = ('Просмотры 👀',
               'Репосты 📢',
               CANCEL_BTN[0])
AUTO_BTNS = ('Добавление 📌',
             'Удаление ❌',
             'Активные 📅',
             CANCEL_BTN[0])
SINGLE_BTNS = ('Активные 📅',
               'Выполненные 📋',
               'Подписки 🔔',
               'Просмотры 👀',
               'Репосты 📢',
               'Удаление ❌',
               'Реакции 😍',
               CANCEL_BTN[0])
BNT_NUM_OPERATION = ('💬 Проверить СМС',
                     '🅾️ Отменить номер')
CREATE_APP_BTN = ('Создать приложение 📱',)
GET_API_CODE_BTN = ('Получить код API 📝',)
BOT = TeleBot(TOKEN_TEST)
REQS_QUEUE = []
ACCOUNTS = []
FINISHED_REQS = []
CUR_REQ = {}
AUTO_VIEWS_DICT = {}
AUTO_REPS_DICT = {}
FAKER = Faker()
init()
seed()
LONG_SLEEP = 15
SHORT_SLEEP = 1
LINK_FORMAT = r'https://t\.me/'
MAX_MINS = 300
TIME_FORMAT = '%Y-%m-%d %H:%M'
ADMIN_CHAT_ID = MY_TG_ID
WARDEN_CHAT_ID = MY_TG_ID
CODE = None
ACC_TO_CHANGE = None
API_CODE = None
LABEL_API_MSG = 'Код подтверждения для сайта.'
MAX_WAIT_CODE = 180
LINK_DECREASE_RATIO = 3
LIMIT_DIALOGS = 1000
MAX_MINS_REQ = 20
SHEET_NAME = 'Тестирование'
EXTRA_SHEET_NAME = 'Дополнительные'
MAX_ACCOUNTS_BUY = 5
URL_SIM = 'https://onlinesim.io/api/'
URL_GET_TARIFFS = URL_SIM + 'getTariffs.php'
URL_BUY = URL_SIM + 'getNum.php'
URL_SMS = URL_SIM + 'getState.php'
URL_CANCEL = URL_SIM + 'setOperationOk.php'
URL_TG = 'https://my.telegram.org/'
URL_API_GET_CODE = URL_TG + 'auth/send_password'
URL_API_LOGIN = URL_TG + 'auth/login'
URL_API_CREATE_APP = URL_TG + 'apps/create'
URL_API_GET_APP = URL_TG + 'apps'
MAX_RECURSION = 25
NUMBER_LAST_FIN = 250
LEFT_CORNER = 'A2'
RIGHT_CORNER = 'H500'
SMALL_RIGHT_CORNER = 'D300'
CONN_ERRORS = (TimeoutError, ServerNotFoundError, gaierror, HttpError, SSLEOFError)
FILE_FINISHED = 'finished.json'
FILE_AUTO_VIEWS = 'auto_views.json'
FILE_AUTO_REPS = 'auto_reps.json'
FILE_ACTIVE = 'active.json'
IMG_PATH = 'random_image.jpg'
LAST_NOTIF_EVENT_HANDLER = datetime.now()
LAST_NOTIF_PROCESSOR = datetime.now()
NOTIF_TIME_DELTA = 30
HOME_KEYCODE = 3
PLATFORM_NAME = 'Android'
DEVICE_NAME = 'Mi'
URL_DEVICE = 'http://127.0.0.1:4723/wd/hub'
UDID = '192.168.1.6:5555'
REQS_PORTION = 10
MIN_LEN_EMAIL = 20
ATTEMPTS_EMAIL = 15
