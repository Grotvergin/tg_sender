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

WELCOME_BTNS = ('Разовые 1️⃣',
                'Автоматические ⏳',
                'Авторизация 🔐',
                'Активные 🦾',
                'Покупка 💰',
                'Добавление ➕')
CANCEL_BTN = ('Меню ↩️',)
AUTO_CHOICE = ('Просмотры 👀',
               'Репосты 📢',
               'Реакции 😮',
               CANCEL_BTN[0])
AUTO_BTNS = ('Добавление 📌',
             'Удаление ❌',
             'Активные 📅',
             CANCEL_BTN[0])
STOP_PROCESS = 'Остановка ⏹️'
SINGLE_BTNS = ('Активные 📅',
               'Выполненные 📋',
               'Подписки 🔔',
               'Просмотры 👀',
               'Репосты 📢',
               'Удаление ❌',
               'Реакции 😍',
               CANCEL_BTN[0])
ALL_REACTIONS = [
    '👍', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱', '😢', '🎉', '🤩', '🙏', '👌',
    '🥱', '😍', '🐳', '🔥', '🌚', '🌭', '💯', '🤣','🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋',
    '😴', '🤓', '👨‍💻', '👀', '🙈', '😇', '😨', '🤝', '🤗', '🫡', '💅', '🤪', '🗿',
    '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷‍', '🤷', '😡'
]
YES_NO_BTNS = ('Да ✅', 'Нет ❌', STOP_PROCESS)
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
AUTO_REAC_DICT = {}
BUYING_INFO = {}
FAKER = Faker()
init()
seed()
ADMIN_CHAT_ID = MY_TG_ID
CODE = None
MIN_LEN_EMAIL = 15
LONG_SLEEP = 15
SHORT_SLEEP = 1
MAX_MINS = 300
MAX_WAIT_CODE = 120
LINK_DECREASE_RATIO = 4
LIMIT_DIALOGS = 1000
MAX_MINS_REQ = 20
MAX_ACCOUNTS_BUY = 10
NOTIF_TIME_DELTA = 30
REQS_PORTION = 10
MAX_RECURSION = 5
NUMBER_LAST_FIN = 250
USER_ANSWER_TIMEOUT = 300
ONLINESIM_CANCEL_BUFFER = 120
ONLINESIM_COMPULSORY_BUFFER = 3
TIME_FORMAT = '%Y-%m-%d %H:%M'
LINK_FORMAT = r'https://t\.me/'
URL_SIM = 'https://onlinesim.io/api/'
URL_GET_TARIFFS = URL_SIM + 'getTariffs.php'
URL_BUY = URL_SIM + 'getNum.php'
URL_SMS = URL_SIM + 'getState.php'
URL_CANCEL = URL_SIM + 'setOperationOk.php'
URL_PROXY = f'https://proxy6.net/api/{PROXY_KEY}/'
URL_GET_PROXY = URL_PROXY + 'getproxy?state=all'
URL_SET_COMMENT_PROXY = URL_PROXY + 'setdescr?'
FILE_FINISHED = 'finished.json'
FILE_AUTO_VIEWS = 'auto_views.json'
FILE_AUTO_REPS = 'auto_reps.json'
FILE_AUTO_REAC = 'auto_reac.json'
FILE_ACTIVE = 'active.json'
IMG_PATH = 'random_image.jpg'
