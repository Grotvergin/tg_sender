from telebot.types import Message
from source import (CANCEL_BTN, WELCOME_BTNS, BNT_NUM_OPERATION,
                    CREATE_APP_BTN, BOT, LONG_SLEEP, FAKER,
                    URL_BUY, MAX_ACCOUNTS_BUY, URL_CANCEL, URL_SMS,
                    URL_API_GET_CODE, URL_API_LOGIN, URL_API_GET_APP,
                    URL_API_CREATE_APP, URL_GET_TARIFFS, LEFT_CORNER,
                    SMALL_RIGHT_CORNER, EXTRA_SHEET_NAME, GET_API_CODE_BTN)
from secret import TOKEN_SIM, SHEET_ID
from common import ShowButtons, Sleep, Stamp, ControlRecursion, UploadData, GetSector, BuildService
from info_senders import SendTariffInfo
from requests import get, Session
from headers_agents import HEADERS
from re import search, MULTILINE, IGNORECASE
from bs4 import BeautifulSoup


def AddAccounts(message: Message) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        req_quantity = int(message.text)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, f'❌ Пожалуйста, введите только число. Введите от 0 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    if req_quantity > MAX_ACCOUNTS_BUY or req_quantity <= 0:
        ShowButtons(message, CANCEL_BTN, f'❌ Введено некорректное число. Введите от 0 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    country_data = GetTariffInfo(message)
    BOT.send_message(message.from_user.id, '📌 Введите код желаемой страны:')
    msg, avail_codes = SendTariffInfo(country_data)
    BOT.send_message(message.from_user.id, msg)
    BOT.register_next_step_handler(message, ChooseCountry, req_quantity, avail_codes)


def ChooseCountry(message: Message, req_quantity: int, avail_codes: list) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        country_code = int(message.text)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, '❌ Пожалуйста, введите только код страны (например, 7):')
        BOT.register_next_step_handler(message, ChooseCountry, req_quantity)
        return
    if country_code not in avail_codes:
        ShowButtons(message, CANCEL_BTN, '❌ Введена некорректная страна. Попробуйте ещё раз:')
        BOT.register_next_step_handler(message, ChooseCountry, req_quantity)
        return
    Stamp(f'Chosen country: {message.text}', 'i')
    BOT.send_message(message.from_user.id, f'🔁 Выбрана страна: {message.text}. Начинаю процесс покупки...')
    AddAccountRecursive(message, 0, req_quantity, country_code)


def AddAccountRecursive(message: Message, current_index: int, total: int, country_code: int) -> None:
    if current_index >= total:
        BOT.send_message(message.from_user.id, f'✅ Было обработано {total} аккаунтов')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    Stamp(f'Adding {current_index + 1} account', 'i')
    BOT.send_message(message.from_user.id, f'▫️ Добавляю {current_index + 1}-й аккаунт')
    try:
        num, tzid = BuyAccount(message, country_code)
    except RecursionError:
        Stamp(f'Exiting because of buying fail', 'w')
        BOT.send_message(message.from_user.id, '❗️ Завершаю процесс покупки...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    ShowButtons(message, BNT_NUM_OPERATION, '❕ Если аккаунт нужно отменить, воспользуйтесь кнопкой')
    BOT.register_next_step_handler(message, AbilityToCancel, num, tzid, current_index, total, country_code)


@ControlRecursion
def BuyAccount(message: Message, country_code: int) -> tuple:
    try:
        response = get(URL_BUY, params={'apikey': TOKEN_SIM, 'service': 'telegram', 'country': country_code, 'number': True, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while buying account: {e}', 'e')
        BOT.send_message(message.from_user.id, f'❌ Не удалось связаться с сервером покупки аккаунтов, '
                                               f'пробую ещё раз через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP)
        num, tzid = BuyAccount(message)
    else:
        if str(response.status_code)[0] == '2':
            if 'number' in response.json():
                num = response.json()['number']
                tzid = response.json()['tzid']
                Stamp(f'Bought account: {num}', 's')
                BOT.send_message(message.from_user.id, f'📱 Куплен номер {num}')
            else:
                Stamp(f'No "number" field in response <-> no available numbers in this region', 'e')
                BOT.send_message(message.from_user.id, '⛔️ Нет доступных номеров в этом регионе, '
                                                       'прекращаю процесс покупки...')
                raise RecursionError
        else:
            Stamp(f'Failed to buy account: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'❌ Не удалось купить аккаунт, '
                                                   f'пробую ещё раз через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP)
            num, tzid = BuyAccount(message)
    return num, tzid


def AbilityToCancel(message: Message, num: str, tzid: str, current_index: int, total: int, country_code: int) -> None:
    if message.text == BNT_NUM_OPERATION[1]:
        Stamp(f'Cancelling number {num}', 'w')
        BOT.send_message(message.from_user.id, f'🆗 Отменяю номер {num} (занимает некоторое время)...')
        try:
            CancelNumber(message, num, tzid)
        except RecursionError:
            Stamp('Too many tries to cancel num, returning', 'w')
            BOT.send_message(message.from_user.id, '🛑 Слишком много попыток отмены номера, '
                                                   'перехожу к следующему...')
        AddAccountRecursive(message, current_index + 1, total, country_code)
        return
    elif message.text == BNT_NUM_OPERATION[0]:
        ProcessAccountSms(message, num, tzid, current_index, total, country_code)
        return


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
    BOT.register_next_step_handler(message, HandleAPICode, session, num, rand_hash)


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
            BOT.send_message(message.from_user.id, f'💬 Код для авторизации в API отправлен на {num}, '
                                                   f'проверьте сообщения от Telegram.\n⚠️ В ответ перешлите мне'
                                                   f'всё сообщение целиком.')
            print(response.json())
            rand_hash = response.json()['random_hash']
        else:
            Stamp(f'Failed to send API code to {num}: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'‼️ Не удалось запросить код для API, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session, rand_hash = RequestAPICode(message, num)
    return session, rand_hash


@ControlRecursion
def CancelNumber(message: Message, num: str, tzid: str) -> None:
    try:
        response = get(URL_CANCEL, params={'apikey': TOKEN_SIM, 'tzid': tzid, 'ban': 1, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while cancelling number {num}: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сервером для отмены номера, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        CancelNumber(message, num, tzid)
    else:
        if str(response.status_code)[0] == '2' and str(response.json()['response']) == '1':
            Stamp(f'Successful cancelling of number {num}', 's')
            BOT.send_message(message.from_user.id, f'❇️ Номер {num} отменён')
        else:
            Stamp(f'Failed to cancel number {num}: {response.text}', 'w')
            BOT.send_message(message.from_user.id, f'ℹ️ Пока что не удалось отменить номер, '
                                                    f'пробую ещё раз через {LONG_SLEEP * 2} секунд...')
            Sleep(LONG_SLEEP * 2)
            CancelNumber(message, num, tzid)


def ProcessAccountSms(message: Message, num: str, tzid: str, current_index: int, total: int, country_code: int) -> None:
    Stamp(f'Checking for all sms', 'i')
    sms_dict = CheckAllSms(message)
    if sms_dict and num in sms_dict:
        Stamp('Found incoming sms for recently bought number', 's')
        BOT.send_message(message.from_user.id, f'📲 Для номера {num} нашёл код: {sms_dict[num]}')
        ShowButtons(message, GET_API_CODE_BTN, '❔ Как будете готовы, нажмите кнопку')
        BOT.register_next_step_handler(message, SendAPICode, num)
    else:
        Stamp(f'No incoming sms for {num}', 'w')
        BOT.send_message(message.from_user.id, f'💤 Не вижу входящих сообщений для {num}')
        ShowButtons(message, BNT_NUM_OPERATION, '❔ Что делаем дальше?')
        BOT.register_next_step_handler(message, AbilityToCancel, num, tzid, current_index, total, country_code)


def CheckAllSms(message: Message) -> dict | None:
    res = {}
    try:
        response = get(URL_SMS, params={'apikey': TOKEN_SIM})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server: {e}', 'e')
        BOT.send_message(message.from_user.id, f'❌ Не удалось связаться с сервером для получения кодов...')
    else:
        if str(response.status_code)[0] == '2':
            Stamp('See some data about sms', 's')
            for item in response.json():
                if 'msg' in item:
                    res[item['number']] = item['msg']
        else:
            Stamp(f'Failed to get list of sms: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'❌ Статус {response.status_code} при обновлении списка смс...')
    return res


@ControlRecursion
def GetTariffInfo(message: Message) -> dict:
    try:
        response = get(URL_GET_TARIFFS, params={'apikey': TOKEN_SIM})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while getting tariffs: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сервером для получения тарифов, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        data = GetTariffInfo(message, TOKEN_SIM)
    else:
        if str(response.status_code)[0] == '2':
            Stamp('Successfully got tariffs', 's')
            BOT.send_message(message.from_user.id, f'🔁 Получил тарифы')
            data = response.json()
        else:
            Stamp(f'Failed to get tariffs: {response.text}', 'w')
            BOT.send_message(message.from_user.id, f'ℹ️ Пока что не удалось получить тарифы, '
                                                    f'пробую ещё раз через {LONG_SLEEP * 2} секунд...')
            Sleep(LONG_SLEEP * 2)
            data = GetTariffInfo(message, TOKEN_SIM)
    return data


def ExtractCodeFromMessage(text: str) -> str | None:
    pattern = r'Вот он:\s*(\S+)'
    found = search(pattern, text, MULTILINE)
    if found:
        return found.group(1)
    return None


def HandleAPICode(message: Message, session: Session, num: str, rand_hash: str) -> None:
    code = ExtractCodeFromMessage(message.text)
    if not code:
        Stamp('No valid API code from user found, exiting...', 'e')
        BOT.send_message(message.from_user.id, '❌ Не удалось извлечь код из сообщения, завершаю процесс покупки...')
        return
    Stamp(f'API code received for number {num}: {code}', 's')
    BOT.send_message(message.from_user.id, f'✳️ Обнаружен код: {code}')
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
    ShowButtons(message, CREATE_APP_BTN, '❔ Нажмите, как будете готовы создать приложение')
    BOT.register_next_step_handler(message, FinalStep, session, num, cur_hash)


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
                                           f'▶️ Заношу данные в таблицу...')
    srv = BuildService()
    row = len(GetSector(LEFT_CORNER, SMALL_RIGHT_CORNER, srv, EXTRA_SHEET_NAME, SHEET_ID)) + 2
    UploadData([[num[1:], api_id, api_hash, '-']], EXTRA_SHEET_NAME, SHEET_ID, srv, row)
    Stamp(f'Data for number {num} added to the table', 's')
    BOT.send_message(message.from_user.id, f'📊 Данные для номера {num} занесены в таблицу')


def GenerateRandomWord(min_length: int) -> str:
    word = FAKER.word()
    while len(word) < min_length:
        word += f's{FAKER.word()}'
    return word


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
