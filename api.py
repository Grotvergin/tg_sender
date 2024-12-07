from pprint import pprint

from headers_agents import HEADERS
from source import (URL_API_GET_CODE, URL_API_LOGIN, URL_API_CREATE_APP,
                    URL_API_GET_APP, BOT, LONG_SLEEP)
from generator import GenerateRandomWord
from common import Stamp, Sleep, ControlRecursion
# ---
from re import search, IGNORECASE
# ---
from requests import Session
from bs4 import BeautifulSoup


@ControlRecursion
def RequestAPICode(user_id: int, num: str, proxy: dict) -> (Session, str):
    Stamp('Sending request to authorize on API', 'i')
    BOT.send_message(user_id, f'📮 Отправляю код на номер {num} для авторизации API')
    session = Session()
    session.proxies = proxy
    test_url = "https://api.ipify.org?format=json"
    response = session.get(test_url, timeout=10)
    response.raise_for_status()
    print(f"Proxy test successful! Response: {response.json()}")
    try:
        response = session.post(URL_API_GET_CODE, headers=HEADERS, data={'phone': num})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while requesting API code: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с API для запроса кода, '
                                  f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session, rand_hash = RequestAPICode(user_id, num, proxy)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Sent API code', 's')
            BOT.send_message(user_id, f'💬 Код для авторизации в API отправлен')
            rand_hash = response.json().get('random_hash')
        else:
            Stamp(f'Failed to send API code: {response.text}', 'e')
            BOT.send_message(user_id, f'‼️ Не удалось запросить код для API, '
                                      f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session, rand_hash = RequestAPICode(user_id, num, proxy)
    Sleep(10, 0.3)
    return session, rand_hash


@ControlRecursion
def LoginAPI(user_id: int, session: Session, num: str, rand_hash: str, code: str) -> Session:
    Stamp('Logging into API', 'i')
    BOT.send_message(user_id, f'🔑 Пытаюсь зайти в API')
    data = {
        'phone': num,
        'random_hash': rand_hash,
        'password': code,
    }
    try:
        response = session.post(URL_API_LOGIN, headers=HEADERS, data=data)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during API login: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с API для авторизации, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session = LoginAPI(user_id, session, num, rand_hash, code)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Login into API', 's')
            BOT.send_message(user_id, f'❇️ Зашёл в API для аккаунта {num}')
        else:
            Stamp(f'Failed to login into API: {response.text}', 'e')
            BOT.send_message(user_id, f'🛑 Не удалось зайти в API, пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session = LoginAPI(user_id, session, num, rand_hash, code)
    return session


def GetHash(user_id: int, session: Session) -> str:
    Stamp('Getting hash', 'i')
    BOT.send_message(user_id, f'🔍 Получаю хеш с сайта...')
    try:
        response = session.get(URL_API_GET_APP, headers=HEADERS)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during hash requesting: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с сайтом для получения хеша, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        cur_hash = GetHash(user_id, session)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Got HTML page for hash', 's')
            BOT.send_message(user_id, f'♻️ Получил страницу сайта, ищу необходимые данные')
            cur_hash = ParseHash(user_id, response.text)
        else:
            Stamp('Did not got HTML page for hash', 'e')
            BOT.send_message(user_id, f'📛 Не удалось получить страницу сайта с хешем, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            cur_hash = GetHash(user_id, session)
    Sleep(LONG_SLEEP, 0.5)
    return cur_hash


def ParseHash(user_id: int, page: str) -> str | None:
    Stamp('Parsing hash from HTML page', 'i')
    BOT.send_message(user_id, '🔍 Ищу хеш на странице...')
    soup = BeautifulSoup(page, 'html.parser')
    hash_input = soup.find('input', {'name': 'hash'})
    if hash_input:
        BOT.send_message(user_id, f'✅ Нашёл хеш: {hash_input.get("value")}')
        Stamp(f'Got hash: {hash_input.get("value")}', 's')
        return hash_input.get('value')
    Stamp('Did not got hash', 'e')
    BOT.send_message(user_id, '❌ Не удалось найти хеш на странице')
    return


@ControlRecursion
def CreateApp(user_id: int, session: Session, num: str, cur_hash: str) -> None:
    Stamp('Creating app', 'i')
    BOT.send_message(user_id, f'🔨 Создаю приложение')
    data = {
        'hash': cur_hash,
        'app_title': GenerateRandomWord(15),
        'app_shortname': GenerateRandomWord(10),
        'app_url': '',
        'app_platform': 'android',
        'app_desc': '',
    }
    try:
        response = session.post(URL_API_CREATE_APP, headers=HEADERS, data=data)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during app creation: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с сервером для создания приложения, '
                                  f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        CreateApp(user_id, session, num, cur_hash)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'App created for number {num}', 's')
            BOT.send_message(user_id, f'🔧 Приложение создано для номера {num}')
        else:
            Stamp(f'Failed to create app for number {num}: {response.text}', 'e')
            BOT.send_message(user_id, f'📛 Не удалось создать приложение для номера {num}')
            raise
    Sleep(LONG_SLEEP, 0.2)


@ControlRecursion
def GetAppData(user_id: int, session: Session) -> (str, str):
    Stamp('Getting app data', 'i')
    BOT.send_message(user_id, f'🔍 Получаю данные о приложении')
    try:
        response = session.get(URL_API_GET_APP, headers=HEADERS)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during app data requesting: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с сайтом данных о приложении, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        api_id, api_hash = GetAppData(user_id, session)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Got HTML page', 's')
            BOT.send_message(user_id, f'♻️ Получил страницу сайта, ищу необходимые данные')
            api_id, api_hash = ParseReadyHTML(response.text)
            Stamp(f'Created an application with {api_id}:{api_hash}', 's')
            BOT.send_message(user_id, f'⚡️ Создал приложение с {api_id}:{api_hash}')
        else:
            Stamp('Did not got HTML page', 'e')
            BOT.send_message(user_id, f'📛 Не удалось получить страницу сайта с API_ID и API_HASH, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            api_id, api_hash = GetAppData(user_id, session)
    return api_id, api_hash


def ParseReadyHTML(page: str) -> (str, str):
    pprint(page)
    api_id_pattern = r'<label for="app_id" class="col-md-4 text-right control-label">App api_id:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*><strong>(\d+)</strong></span>'
    api_hash_pattern = r'<label for="app_hash" class="col-md-4 text-right control-label">App api_hash:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*>([a-f0-9]{32})</span>'
    api_id_match = search(api_id_pattern, page, IGNORECASE)
    api_hash_match = search(api_hash_pattern, page, IGNORECASE)
    api_id = api_id_match.group(1) if api_id_match else None
    api_hash = api_hash_match.group(1) if api_hash_match else None
    return api_id, api_hash
