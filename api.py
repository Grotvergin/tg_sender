import source
from emulator import PressButton, PrepareDriver, IsElementPresent, ExtractCodeFromMessage
from headers_agents import HEADERS
from source import (URL_API_GET_CODE, URL_API_LOGIN, URL_API_CREATE_APP,
                    MAX_WAIT_CODE, URL_API_GET_APP, BOT, LONG_SLEEP, WELCOME_BTNS)
from generator import GenerateRandomWord
from common import Stamp, Sleep, ControlRecursion, ShowButtons
# ---
from re import search, IGNORECASE
from datetime import datetime
# ---
from requests import Session
from telebot.types import Message
from appium.webdriver.common.appiumby import AppiumBy
from bs4 import BeautifulSoup


def SendAPICode(message: Message, num: str) -> None:
    Stamp('Sending request to authorize on API', 'i')
    BOT.send_message(message.from_user.id, f'📮 Отправляю код на номер {num} для авторизации API')
    try:
        session, rand_hash = RequestAPICode(message, num)
    except RecursionError:
        Stamp(f'Exiting because of requesting code fail', 'w')
        BOT.send_message(message.from_user.id, '❗️ Превышено максимальное количество попыток,'
                                               'завершаю процесс покупки...')
        return
    Sleep(10)
    start_time = datetime.now()
    driver = PrepareDriver()
    code = None
    PressButton(driver, 'new UiSelector().className("android.view.ViewGroup").index(0)', 'Chat', 3, by=AppiumBy.ANDROID_UIAUTOMATOR)
    while (datetime.now() - start_time).seconds < MAX_WAIT_CODE:
        if IsElementPresent(driver, 'new UiSelector().textContains("Код")', by=AppiumBy.ANDROID_UIAUTOMATOR):
            code = ExtractCodeFromMessage(driver)
            Stamp(f'API code received for number {num}: {code}', 's')
            BOT.send_message(message.from_user.id, f'✳️ Обнаружен код: {code}')
            break
        Sleep(1)
    if not code:
        Stamp('No API code received', 'e')
        BOT.send_message(message.from_user.id, '❌ Не удалось получить код для API, завершаю процесс покупки...')
        return
    HandleAPICode(message, session, num, rand_hash, code)


@ControlRecursion
def RequestAPICode(message: Message, num: str) -> (Session, str):
    session = Session()
    try:
        response = session.post(URL_API_GET_CODE, headers=HEADERS, data={'phone': num})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while requesting API code: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с API для запроса кода, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session, rand_hash = RequestAPICode(message, num)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Sent API code to {num}', 's')
            BOT.send_message(message.from_user.id, f'💬 Код для авторизации в API отправлен на {num}')
            rand_hash = response.json()['random_hash']
        else:
            Stamp(f'Failed to send API code to {num}: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'‼️ Не удалось запросить код для API, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session, rand_hash = RequestAPICode(message, num)
    return session, rand_hash


def HandleAPICode(message: Message, session: Session, num: str, rand_hash: str, code: str) -> None:
    try:
        session = LoginAPI(message, session, num, rand_hash, code)
    except RecursionError as e:
        Stamp(f'Failed to login into API: {e}', 'e')
        BOT.send_message(message.from_user.id, f'🚫 Не удалось авторизоваться в API с номера {num}, '
                                               f'перехожу к следующему номеру...')
        return
    Stamp(f'Getting hash for account {num}', 'i')
    BOT.send_message(message.from_user.id, f'🔑 Получаю хеш для аккаунта {num}')
    try:
        cur_hash = GetHash(message, session)
    except RecursionError as e:
        Stamp(f'Failed to get hash: {e}', 'e')
        BOT.send_message(message.from_user.id, f'❌ Не удалось получить хеш для аккаунта {num}, '
                                               f'завершаю процесс покупки...')
        return
    FinalStep(message, session, num, cur_hash)


@ControlRecursion
def LoginAPI(message: Message, session: Session, num: str, rand_hash: str, code: str) -> Session:
    data = {
        'phone': num,
        'random_hash': rand_hash,
        'password': code,
    }
    try:
        response = session.post(URL_API_LOGIN, headers=HEADERS, data=data)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during API login: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с API для авторизации, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session = LoginAPI(message, session, num, rand_hash, code)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Logined into API for number {num}', 's')
            BOT.send_message(message.from_user.id, f'❇️ Зашёл в API для аккаунта {num}')
        else:
            Stamp(f'Failed to login into API: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'🛑 Не удалось зайти в API для номера {num}, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session = LoginAPI(message, session, num, rand_hash, code)
    return session


def GetHash(message: Message, session: Session) -> str:
    try:
        response = session.get(URL_API_GET_APP, headers=HEADERS)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during hash requesting: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сайтом для получения хеша, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        cur_hash = GetHash(message, session)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Got HTML page for hash', 's')
            BOT.send_message(message.from_user.id, f'♻️ Получил страницу сайта, ищу необходимые данные')
            cur_hash = ParseHash(message, response.text)
        else:
            Stamp('Did not got HTML page for hash', 'e')
            BOT.send_message(message.from_user.id, f'📛 Не удалось получить страницу сайта с хешем, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            cur_hash = GetHash(message, session)
    return cur_hash


def ParseHash(message: Message, page: str) -> str | None:
    Stamp('Parsing hash from HTML page', 'i')
    BOT.send_message(message.from_user.id, '🔍 Ищу хеш на странице...')
    soup = BeautifulSoup(page, 'html.parser')
    hash_input = soup.find('input', {'name': 'hash'})
    if hash_input:
        BOT.send_message(message.from_user.id, f'✅ Нашёл хеш: {hash_input.get("value")}')
        Stamp(f'Got hash: {hash_input.get("value")}', 's')
        return hash_input.get('value')
    Stamp('Did not got hash', 'e')
    BOT.send_message(message.from_user.id, '❌ Не удалось найти хеш на странице')
    return None


def FinalStep(message: Message, session: Session, num: str, cur_hash: str) -> None:
    Stamp(f'Creating app for account {num}', 'i')
    BOT.send_message(message.from_user.id, f'🔨 Создаю приложение для аккаунта {num}')
    try:
        CreateApp(message, session, num, cur_hash)
    except RecursionError as e:
        Stamp(f'Failed to create app: {e}', 'e')
        BOT.send_message(message.from_user.id, f'📛 Не удалось создать приложение для аккаунта {num}')
        return
    BOT.send_message(message.from_user.id, f'✅ Приложение создано для аккаунта {num}, жду {LONG_SLEEP} секунд...')
    Sleep(LONG_SLEEP)
    Stamp(f'Getting HTML page for number {num}', 'i')
    BOT.send_message(message.from_user.id, f'⏩ Получаю данные об API_ID и API_HASH...')
    try:
        api_id, api_hash = GetAppData(message, session)
    except RecursionError:
        Stamp(f'Exiting because of getting app data fail', 'w')
        BOT.send_message(message.from_user.id, '❗️ Превышено максимальное количество попыток,'
                                               'завершаю процесс покупки...')
        return
    Stamp(f'Got api_id: {api_id} and api_hash: {api_hash} for number {num}', 's')
    BOT.send_message(message.from_user.id, f'✅ Получил данные для номера {num}:\n'
                                           f'API_ID: {api_id}\n'
                                           f'API_HASH: {api_hash}\n'
                                           f'▶️ Начинаю авторизацию и изменение аккаунта...')
    source.ACC_TO_CHANGE = num + '|' + api_id + '|' + api_hash
    ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def CreateApp(message: Message, session: Session, num: str, cur_hash: str) -> None:
    data = {
        'hash': cur_hash,
        'app_title': GenerateRandomWord(10),
        'app_shortname': GenerateRandomWord(7),
        'app_url': '',
        'app_platform': 'android',
        'app_desc': '',
    }
    try:
        response = session.post(URL_API_CREATE_APP, headers=HEADERS, data=data)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during app creation: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сервером для создания приложения, '
                                               f'перехожу к следующему номеру...')
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'App created for number {num}', 's')
            BOT.send_message(message.from_user.id, f'🔧 Приложение создано для номера {num}')
        else:
            Stamp(f'Failed to create app for number {num}: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'📛 Не удалось создать приложение для номера {num}')


@ControlRecursion
def GetAppData(message: Message, session: Session) -> (str, str):
    try:
        response = session.get(URL_API_GET_APP, headers=HEADERS)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during app data requesting: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сайтом данных о приложении, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        api_id, api_hash = GetAppData(message, session)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Got HTML page', 's')
            BOT.send_message(message.from_user.id, f'♻️ Получил страницу сайта, ищу необходимые данные')
            api_id, api_hash = ParseReadyHTML(response.text)
        else:
            Stamp('Did not got HTML page', 'e')
            BOT.send_message(message.from_user.id, f'📛 Не удалось получить страницу сайта с API_ID и API_HASH, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            api_id, api_hash = GetAppData(message, session)
    return api_id, api_hash


def ParseReadyHTML(page: str) -> (str, str):
    api_id_pattern = r'<label for="app_id" class="col-md-4 text-right control-label">App api_id:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*><strong>(\d+)</strong></span>'
    api_hash_pattern = r'<label for="app_hash" class="col-md-4 text-right control-label">App api_hash:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*>([a-f0-9]{32})</span>'
    api_id_match = search(api_id_pattern, page, IGNORECASE)
    api_hash_match = search(api_hash_pattern, page, IGNORECASE)
    api_id = api_id_match.group(1) if api_id_match else 'Не нашёл!'
    api_hash = api_hash_match.group(1) if api_hash_match else 'Не нашёл!'
    return api_id, api_hash
