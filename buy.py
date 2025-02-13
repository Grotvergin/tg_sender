import source
from auth import AuthCallback
from generator import GenerateRandomRussianName, GenerateRandomWord
from source import (CANCEL_BTN, WELCOME_BTNS, BOT, LONG_SLEEP, ONLINESIM_COMPULSORY_BUFFER,
                    URL_BUY, MAX_ACCOUNTS_BUY, URL_CANCEL, URL_SMS, URL_GET_TARIFFS,
                    MAX_WAIT_CODE, SHORT_SLEEP, USER_RESPONSES, USER_ANSWER_TIMEOUT, YES_NO_BTNS,
                    MAX_RECURSION, MIN_LEN_EMAIL, STOP_PROCESS, ONLINESIM_CANCEL_BUFFER)
from common import (ShowButtons, Sleep, Stamp, ControlRecursion, CancelAndNext,
                    GoNextOnly, BuildService, GetSector, UploadData, FinishProcess)
from secret import TOKEN_SIM, PASSWORD, SHEET_NAME, SHEET_ID
from info_senders import SendTariffInfo
from change import SetProfileInfo, SetProfilePicture, AddContacts, UpdatePrivacySettings
from proxy import getProxyByComment, setProxyComment
# ---
from asyncio import sleep as async_sleep, Queue, TimeoutError, wait_for
from time import time
from os import getcwd
from os.path import join
from re import search
# ---
from requests import get, post
from telebot.types import Message
from telethon.sync import TelegramClient
from telethon.errors import PeerIdInvalidError
from telethon.tl.functions.contacts import DeleteContactsRequest, ImportContactsRequest
from telethon.tl.types import InputPhoneContact


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
                                                   f'пробую ещё раз через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP)
            data = GetTariffInfo(message, TOKEN_SIM)
    return data


def AddAccounts(message: Message) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        req_quantity = int(message.text)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, f'❌ Пожалуйста, введите только число. Введите от 1 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    if req_quantity > MAX_ACCOUNTS_BUY or req_quantity <= 0:
        ShowButtons(message, CANCEL_BTN, f'❌ Введено некорректное число. Введите от 1 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    country_data = GetTariffInfo(message)
    BOT.send_message(message.from_user.id, '📌 Введите код желаемой страны:')
    msg, avail_codes = SendTariffInfo(country_data)
    BOT.send_message(message.from_user.id, msg, parse_mode='Markdown')
    BOT.register_next_step_handler(message, ChooseCountry, req_quantity, avail_codes)


def ChooseCountry(message: Message, req_quantity: int, avail_codes: list) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        country_code = int(message.text)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, '❌ Пожалуйста, введите только код страны (например, 7):')
        BOT.register_next_step_handler(message, ChooseCountry, req_quantity, avail_codes)
        return
    if country_code not in avail_codes:
        ShowButtons(message, CANCEL_BTN, '❌ Введена некорректная страна. Попробуйте ещё раз:')
        BOT.register_next_step_handler(message, ChooseCountry, req_quantity, avail_codes)
        return
    Stamp(f'Chosen country: {message.text}', 'i')
    BOT.send_message(message.from_user.id, f'🔁 Выбрана страна {message.text}')
    source.BUYING_INFO = {'user_id': message.from_user.id, 'req_quantity': req_quantity, 'country_code': country_code, 'is_buy': True}


async def CheckRefreshBuy() -> None:
    while True:
        if source.BUYING_INFO:
            await ProcessAccounts(**source.BUYING_INFO)
            source.BUYING_INFO = None
        await async_sleep(SHORT_SLEEP)


async def getUserInput(user_id: int) -> str:
    if user_id not in USER_RESPONSES:
        USER_RESPONSES[user_id] = Queue()
    try:
        response = await wait_for(USER_RESPONSES[user_id].get(), USER_ANSWER_TIMEOUT)
        USER_RESPONSES.pop(user_id, None)
        return response.strip()
    except TimeoutError:
        BOT.send_message(user_id, "⏳ Превышено время ожидания ответа.")


def ExtractAutomationCode(user_id: int, text: str):
    code_match = search(r'\b\d{5}\b', text)
    if code_match:
        code = code_match.group(0)
        Stamp(f'Automation code found: {code}', 's')
        BOT.send_message(user_id, f'✳️ Найден код для авторизации юзербота: {code}')
        return code
    Stamp('Automation code was not found in message', 'w')
    BOT.send_message(user_id, '🛑 В сообщении не обнаружено кода для авторизация юзербота')
    raise GoNextOnly


async def AccountExists(user_id: int, client: TelegramClient, phone_number: str) -> bool:
    try:
        first_name, last_name = GenerateRandomRussianName()
        contact = InputPhoneContact(client_id=0, phone=phone_number, first_name=first_name, last_name=last_name)
        result = await client(ImportContactsRequest([contact]))
        if result.imported:
            entity = result.users[0]
            Stamp('Such account already exists', 'w')
            BOT.send_message(user_id, '🟥 Аккаунт уже есть')
            await client(DeleteContactsRequest([entity.id]))
            return True
        else:
            Stamp('Such account does not exist', 's')
            BOT.send_message(user_id, '🟩 Аккаунт не найден')
            return False
    except (PeerIdInvalidError, ValueError):
        Stamp('Such account does not exist', 's')
        BOT.send_message(user_id, '🟨 Аккаунт не существует (сообщите админу и продолжайте)')
        return False
    except Exception as e:
        Stamp(f'Error when checking for existence: {e}', 'e')
        BOT.send_message(user_id, '🟧 Ошибка при проверке на существование аккаунта')


async def ProcessAccounts(user_id: int, req_quantity: int, country_code: int, is_buy: bool) -> None:
    i = 0
    srv = BuildService()
    while i < req_quantity:
        Stamp(f'Adding/buying {i + 1} account', 'i')
        BOT.send_message(user_id, f'▫️ Добавляю/покупаю {i + 1}-й аккаунт')
        try:
            await ProcessSingleAccount(user_id, country_code, srv, is_buy)
            i += 1
            if i < req_quantity:
                ShowButtons(user_id, YES_NO_BTNS, f'❔ Добавляем/покупаем аккаунт №{i + 1}?')
                answer = await getUserInput(user_id)
                if answer == YES_NO_BTNS[1]:
                    break
        except CancelAndNext as e:
            Stamp(f'Waiting for {e.time_to_wait} seconds, cancelling and going on', 'w')
            BOT.send_message(user_id, f'❗️Жду {e.time_to_wait} секунд, отменяю номер и перехожу к следующему')
            Sleep(e.time_to_wait)
            if not CancelNumber(user_id, e.tzid):
                Stamp(f'Exiting because unable to cancel account', 'w')
                BOT.send_message(user_id, '📛 Не получилось отменить номер, завершаю процесс')
                break
        except GoNextOnly:
            Stamp(f'Account {i + 1} requires password or already registered', 'w')
            BOT.send_message(user_id, f'❌ Аккаунт {i + 1} обработать не удалось, перехожу к следующему без возврата')
        except RecursionError:
            Stamp(f'Exiting because of recursion error', 'w')
            BOT.send_message(user_id, '❗️ Завершаю процесс покупки из-за рекурсивной ошибки')
            break
        except FinishProcess:
            Stamp('Process was stopped', 'w')
            BOT.send_message(user_id, '⏹️ Завершаю процесс')
            break
        except Exception as e:
            Stamp(f'Error while adding accounts: {e}', 'e')
            BOT.send_message(user_id, f'❌ Произошла неизвестная ошибка при добавлении аккаунта {i + 1}, завершаю процесс')
            break
    ShowButtons(user_id, WELCOME_BTNS, '❔ Выберите действие:')


async def askToProceed(user_id: int, buttons: tuple, text: str, condition: str, exception) -> str:
    ShowButtons(user_id, buttons, text, parse_mode='Markdown')
    answer = await getUserInput(user_id)
    if answer == condition:
        raise exception
    elif answer == STOP_PROCESS:
        raise FinishProcess
    return answer


def GetTemporaryEmail(min_len: int, password: str) -> (str, str):
    Stamp('Getting temporary email', 'i')
    response = get('https://api.mail.tm/domains')
    domain = response.json()['hydra:member'][0]['domain']
    email_username = GenerateRandomWord(min_len)
    email = f'{email_username}@{domain}'
    data = {
        "address": email,
        "password": password
    }
    post('https://api.mail.tm/accounts', json=data)
    token_response = post('https://api.mail.tm/token', json=data)
    token = token_response.json()['token']
    Stamp(f'Temporary email {email} received successfully', 's')
    return email, token


def GetEmailCode(token: str, max_attempts: int = MAX_RECURSION) -> str | None:
    Stamp('Getting email code', 'i')
    for _ in range(max_attempts):
        response = get('https://api.mail.tm/messages', headers={'Authorization': f'Bearer {token}'})
        messages = response.json()['hydra:member']
        if messages:
            Stamp('Email message received', 's')
            code_message = messages[0]['subject']
            match = search(r'\b\d{6}\b', code_message)
            if match:
                Stamp('Email code received successfully', 's')
                return match.group(0)
            else:
                Stamp('Email code not found in the message', 'w')
        Sleep(SHORT_SLEEP * 5)
    Stamp('Failed to get email code', 'w')
    return


def remainingTime(start):
    elapsed = time() - start
    return int(max(ONLINESIM_CANCEL_BUFFER - elapsed, ONLINESIM_COMPULSORY_BUFFER))


async def ProcessSingleAccount(user_id: int, country_code: int, srv, is_buy: bool):
    start = time()
    if is_buy:
        num, tzid = BuyAccount(user_id, country_code)
        if await AccountExists(user_id, source.ACCOUNTS[0], num):
            raise CancelAndNext(tzid, remainingTime(start))
        await askToProceed(user_id, YES_NO_BTNS, f'🖊 Ввод `{num}`?', YES_NO_BTNS[1], CancelAndNext(tzid, remainingTime(start)))
        code = GetCodeFromSms(user_id, num, tzid)
        await askToProceed(user_id, YES_NO_BTNS, f'🖊 Ввод `{code}`?', YES_NO_BTNS[1], GoNextOnly)
        await askToProceed(user_id, YES_NO_BTNS, f'🖊 Ввод пароля `{PASSWORD}`?', YES_NO_BTNS[1], GoNextOnly)
        email, token = GetTemporaryEmail(MIN_LEN_EMAIL, PASSWORD)
        await askToProceed(user_id, YES_NO_BTNS, f'🖊 Ввод email `{email}`?', YES_NO_BTNS[1], GoNextOnly)
        code = GetEmailCode(token)
        await askToProceed(user_id, YES_NO_BTNS, f'🖊 Ввод `{code}`?', YES_NO_BTNS[1], GoNextOnly)
    else:
        num = await askToProceed(user_id, CANCEL_BTN, '🖊 Введите номер в формате `79151234567`', CANCEL_BTN[0], FinishProcess)
    num = num.replace('+', '')
    socks_proxy, proxy_id = getProxyByComment(user_id, '')
    setProxyComment(user_id, proxy_id, 'busy')
    row = len(GetSector('C2', 'C500', srv, SHEET_NAME, SHEET_ID)) + 2
    api_id, api_hash = GetSector(f'A{row}', f'B{row}', srv, SHEET_NAME, SHEET_ID)[0]
    UploadData(f'C{row}', f'H{row}', [[num, PASSWORD, socks_proxy[1], socks_proxy[2], socks_proxy[4], socks_proxy[5]]], SHEET_NAME, SHEET_ID, srv)
    BOT.send_message(user_id, '📊 Данные занесены в таблицу')
    session = join(getcwd(), 'sessions', f'{num}')
    client = TelegramClient(session, api_id, api_hash, proxy=socks_proxy)
    await client.start(phone=num, password=PASSWORD, code_callback=lambda: AuthCallback(num, user_id, MAX_WAIT_CODE))
    Stamp('Account authorized', 's')
    BOT.send_message(user_id, '✅ Аккаунт авторизован')
    await SetProfileInfo(client, user_id)
    await SetProfilePicture(client, user_id)
    await AddContacts(client, 50, user_id)
    await UpdatePrivacySettings(client, user_id)
    source.ACCOUNTS.append(client)


@ControlRecursion
def BuyAccount(user_id: int, country_code: int) -> tuple:
    Stamp('Trying to buy account', 'i')
    BOT.send_message(user_id, '📲 Покупаю номер...')
    try:
        response = get(URL_BUY, params={'apikey': TOKEN_SIM, 'service': 'telegram', 'country': country_code, 'number': True, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while buying account: {e}', 'e')
        BOT.send_message(user_id, f'❌ Не удалось связаться с сервером покупки аккаунтов, '
                                  f'пробую ещё раз через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP)
        num, tzid = BuyAccount(user_id)
    else:
        if str(response.status_code)[0] == '2':
            if 'number' in response.json():
                num = response.json()['number']
                tzid = response.json()['tzid']
                Stamp(f'Bought account: {num}', 's')
            else:
                Stamp(f'No "number" field in response', 'e')
                BOT.send_message(user_id, '⛔️ Проблема при покупке номера')
                raise
        else:
            Stamp(f'Failed to buy account: {response.text}', 'e')
            BOT.send_message(user_id, f'❌ Не удалось купить аккаунт, '
                                      f'пробую ещё раз через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP)
            num, tzid = BuyAccount(user_id)
    return num, tzid


def CancelNumber(user_id: int, tzid: str) -> bool:
    for attempt in range(MAX_RECURSION):
        try:
            response = get(URL_CANCEL, params={'apikey': TOKEN_SIM, 'tzid': tzid, 'lang': 'ru'})
            if response.status_code // 100 == 2 and str(response.json().get('response')) == '1':
                Stamp(f'Successfully canceled number', 's')
                BOT.send_message(user_id, f'❇️ Номер отменён')
                return True
            else:
                Stamp(f'Failed to cancel number. Response: {response.text}', 'w')
                BOT.send_message(user_id, f'ℹ️ Попытка отменить номер не удалась. Пробую снова...')
        except ConnectionError as e:
            Stamp(f'Failed to connect to the server while cancelling number: {e}', 'e')
            BOT.send_message(user_id, f'‼️ Не удалось связаться с сервером для отмены номера. '
                                      f'Пробую снова примерно через {LONG_SLEEP} секунд...')
        finally:
            Sleep(LONG_SLEEP, 0.5)
    return False


def GetCodeFromSms(user_id: int, num: str, tzid: str) -> str:
    start_time = time()
    while time() - start_time < MAX_WAIT_CODE:
        sms_dict = CheckAllSms(user_id)
        if sms_dict and num in sms_dict:
            Stamp(f'Found incoming sms for num {num}', 's')
            BOT.send_message(user_id, f'🔔 Нашёл код')
            return sms_dict[num]
        Stamp(f'No incoming sms for {num} after {round(time() - start_time)} seconds of waiting', 'w')
        BOT.send_message(user_id, f'💤 Не вижу входящих сообщений после {round(time() - start_time)} секунд ожидания...')
        Sleep(LONG_SLEEP)
    raise CancelAndNext(tzid, ONLINESIM_COMPULSORY_BUFFER)


def CheckAllSms(user_id: int) -> dict | None:
    res = {}
    try:
        response = get(URL_SMS, params={'apikey': TOKEN_SIM})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server: {e}', 'e')
        BOT.send_message(user_id, f'❌ Не удалось связаться с сервером для получения кодов...')
    else:
        if str(response.status_code)[0] == '2':
            for item in response.json():
                if 'msg' in item:
                    res[item['number']] = item['msg']
        else:
            Stamp(f'Failed to get list of sms: {response.text}', 'e')
            BOT.send_message(user_id, f'❌ Статус {response.status_code} при обновлении списка смс...')
    return res
