from secret import TOKEN, MY_TG_ID, PROXY_KEY
# ---
from random import seed
from ssl import SSLEOFError
from socket import gaierror
from datetime import datetime
# ---
from httplib2.error import ServerNotFoundError
from telebot import TeleBot
from colorama import init
from faker import Faker
from googleapiclient.errors import HttpError

# ----- TODO LIST -----
# Кнопка для возврата заявки
# Заявки на эмодзи

WELCOME_BTNS = ('Разовые 1️⃣',
                'Автоматические ⏳',
                'Авторизация 🔐',
                'Активные 🦾',
                'Покупка 💰')
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
YES_NO_BTNS = ('Да ✅', 'Нет ❌')
PROBLEM_BTN = ('Проблема ⚠️',)
SKIP_CODE = ('Пропуск ⏭️',)
BOT = TeleBot(TOKEN)
CONN_ERRORS = (TimeoutError, ServerNotFoundError, gaierror, HttpError, SSLEOFError)
LAST_NOTIF_PROCESSOR = datetime.now()
USER_RESPONSES = {}
REQS_QUEUE = []
ACCOUNTS = []
FINISHED_REQS = []
CUR_REQ = {}
AUTO_VIEWS_DICT = {}
AUTO_REPS_DICT = {}
BUYING_INFO = {}
FAKER = Faker()
init()
seed()
ADMIN_CHAT_ID = MY_TG_ID
CODE = None
MIN_LEN_EMAIL = 15
LEN_API_CODE = 11
LONG_SLEEP = 15
SHORT_SLEEP = 1
MAX_MINS = 300
MAX_WAIT_CODE = 121
LINK_DECREASE_RATIO = 3
LIMIT_DIALOGS = 1000
MAX_MINS_REQ = 20
MAX_ACCOUNTS_BUY = 10
NOTIF_TIME_DELTA = 30
REQS_PORTION = 10
MIN_LEN_EMAIL = 15
MAX_RECURSION = 10
NUMBER_LAST_FIN = 250
USER_ANSWER_TIMEOUT = 300
TIME_FORMAT = '%Y-%m-%d %H:%M'
LINK_FORMAT = r'https://t\.me/'
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
URL_PROXY = 'https://api.dashboard.proxy.market/dev-api/'
URL_BUY_PROXY = URL_PROXY + f'buy-proxy/{PROXY_KEY}'
URL_RECEIVE_PROXY = URL_PROXY + f'list/{PROXY_KEY}'
LEFT_CORNER = 'A2'
RIGHT_CORNER = 'H500'
FILE_FINISHED = 'finished.json'
FILE_AUTO_VIEWS = 'auto_views.json'
FILE_AUTO_REPS = 'auto_reps.json'
FILE_ACTIVE = 'active.json'
IMG_PATH = 'random_image.jpg'
KEY_PHRASE = 'Вот он:'
