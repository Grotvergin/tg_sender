from secret import TOKEN, MY_TG_ID, PROXY_KEY, TOKEN_TEST
# ---
from random import seed
from ssl import SSLEOFError
from socket import gaierror
from datetime import datetime
from asyncio import Semaphore
from collections import defaultdict
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
                'Добавление ➕',
                'Ручной ввод 🔰',
                'Ребрендинг 🧼',
                'Проверка подписок ⛑')
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
HANDLERS = {}
SKIP_CODE = ('Пропуск ⏭️',)
DEFAULT_MAX_UNIQ_REAC = 5
MAX_CONCURRENT_REQS = 10
PERMANENT_LOCK_BUFFER = 100
REFRESH_HANDLER_TIMEOUT_MIN = 60
TIME_FRACTION = 0.05
ACCOUNTS_LEN = 0
MONITOR_INTERVAL_MINS = 10
POSTS_TO_CHECK = 10
TIMEOUT_CHECK_AVAILABLE = 300
MIN_LEN_EMAIL = 15
LONG_SLEEP = 15
SHORT_SLEEP = 1
MAX_MINS = 300
MAX_WAIT_CODE = 120
LINK_DECREASE_RATIO = 4
LIMIT_DIALOGS = 2000
MAX_MINS_REQ = 10
MAX_ACCOUNTS_BUY = 10
NOTIF_TIME_DELTA = 5
REQS_PORTION = 10
MAX_RECURSION = 5
NUMBER_LAST_FIN = 250
USER_ANSWER_TIMEOUT = 300
ONLINESIM_CANCEL_BUFFER = 120
ONLINESIM_COMPULSORY_BUFFER = 3
CHECK_INTERVAL = 30
MAX_SILENCE_TIME = 10
MIN_DIFF_REAC_NORMAL = 4
MAX_DIFF_REAC_NORMAL = 7
MIN_DIFF_REAC_DECREASED = 2
MAX_DIFF_REAC_DECREASED = 4
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
AUTHORIZED_USERS_FILE = "authorized_users.json"
EMERGENCY_FILE = 'emerge.json'
DAILY_STATS_FILE = 'daily.json'
NO_REQUIREMENTS_MESSAGE = 'нет заявки'
LAST_MAIN_CHECK_FILE = "last_main_check.json"
LAST_ANOMALY_CHECK_FILE = "last_anomaly_check.json"
MAIN_BOT_TYPE = 'main'
ANOMALY_BOT_TYPE = 'anomaly'
MONITOR_TYPES = ('m', 'a')
BOT = TeleBot(TOKEN)
CONN_ERRORS = (TimeoutError, ServerNotFoundError, gaierror, HttpError, SSLEOFError)
LAST_NOTIF_PROCESSOR = datetime.now()
USER_RESPONSES = {}
REQS_QUEUE = []
ACCOUNTS = []
SEMAPHORE = Semaphore(MAX_CONCURRENT_REQS)
LOCKS = {}
FINISHED_REQS = []
CUR_REQ = {}
AUTO_VIEWS_DICT = {}
AUTO_REPS_DICT = {}
AUTO_REAC_DICT = {}
BUYING_INFO = {}
AUTHORIZED_USERS = set()
FAKER = Faker()
DAILY_STATS = defaultdict(int)
LAST_STATS_RESET = datetime.now().date()
init()
seed()
ADMIN_CHAT_ID = MY_TG_ID
CODE = None
MANUAL_CHANNEL_LINK = None
MANUAL_CHANNEL_USER = None
CHECK_CHANNEL_USER = None
CHECK_CHANNEL_LINK = None
CHECKED_AVAILABLE_COUNT = None
CODE_REQUEST_READY = False
