import source
from source import (CANCEL_BTN, WELCOME_BTNS, BOT, LEFT_CORNER, RIGHT_CORNER,
                    LONG_SLEEP, URL_BUY, MAX_ACCOUNTS_BUY, URL_CANCEL,
                    URL_SMS, URL_GET_TARIFFS, MAX_WAIT_CODE, SHORT_SLEEP)
from common import (ShowButtons, Sleep, Stamp, ControlRecursion, ErrorAfterNumberInsertion,
                    PasswordRequired, BuildService, GetSector, UploadData)
from api import GetAPICode, RequestAPICode, LoginAPI, GetHash, CreateApp, GetAppData
from emulator import AskForCode, InsertCode, PrepareDriver, SetPassword, PressButton, ExitFromAccount
from secret import TOKEN_SIM, PASSWORD, SHEET_NAME, SHEET_ID
from info_senders import SendTariffInfo
from change import (SetProfileInfo, SetProfilePicture, AddContacts, UpdatePrivacySettings,
                    buyProxy, receiveProxyInfo, emuAuthCallback)
# ---
from asyncio import sleep as async_sleep
from time import time
from os import getcwd
from os.path import join
# ---
from requests import get
from telebot.types import Message
from appium.webdriver import Remote
from telethon.sync import TelegramClient


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
    source.BUYING_INFO = {'user_id': message.from_user.id, 'req_quantity': req_quantity, 'country_code': country_code}


async def CheckRefreshBuy() -> None:
    while True:
        if source.BUYING_INFO:
            await ProcessAccounts(**source.BUYING_INFO)
            source.BUYING_INFO = None
        await async_sleep(SHORT_SLEEP)


async def ProcessAccounts(user_id: int, req_quantity: int, country_code: int) -> None:
    i = 0
    driver = PrepareDriver()
    srv = BuildService()
    while i < req_quantity:
        Stamp(f'Adding {i + 1} account', 'i')
        BOT.send_message(user_id, f'▫️ Добавляю {i + 1}-й аккаунт')
        try:
            num, tzid = BuyAccount(user_id, country_code)
            AskForCode(driver, num, user_id, len(str(country_code)))
            code = GetCodeFromSms(driver, user_id, num)
            InsertCode(driver, user_id, code)
            session, rand_hash = RequestAPICode(user_id, num)
            code = GetAPICode(driver, user_id, num)
            LoginAPI(user_id, session, num, rand_hash, code)
            cur_hash = GetHash(user_id, session)
            CreateApp(user_id, session, num, cur_hash)
            api_id, api_hash = GetAppData(user_id, session)
            SetPassword(driver, user_id)
            buyProxy(user_id)
            proxy = receiveProxyInfo(user_id)
            num = num[1:]
            session = join(getcwd(), 'sessions', f'{num}')
            client = TelegramClient(session, api_id, api_hash)
            await client.start(phone=num, password=PASSWORD, code_callback=lambda: emuAuthCallback(driver))
            Stamp(f'Account {num} authorized', 's')
            BOT.send_message(user_id, f'✅ Аккаунт {num} авторизован')
            source.ACCOUNTS.append(client)
            await SetProfileInfo(client, user_id)
            await SetProfilePicture(client, user_id)
            await AddContacts(client, 50, user_id)
            await UpdatePrivacySettings(client, user_id)
            row = len(GetSector(LEFT_CORNER, RIGHT_CORNER, srv, SHEET_NAME, SHEET_ID)) + 2
            UploadData([[num, api_id, api_hash, PASSWORD, proxy[1], proxy[2], proxy[4], proxy[5]]], SHEET_NAME, SHEET_ID, srv, row)
            BOT.send_message(user_id, f'📊 Данные для номера {num} занесены в таблицу')
            ExitFromAccount(driver)
            i += 1
        except ErrorAfterNumberInsertion:
            Stamp(f'Account {i + 1} has problems when requesting code', 'w')
            BOT.send_message(user_id, f'❌ В аккаунте {i + 1} проблема при запросе кода, отменяю и перехожу к следующему...')
            try:
                CancelNumber(user_id, num, tzid)
                continue
            except RecursionError:
                Stamp(f'Exiting because unable to cancel account', 'w')
                BOT.send_message(user_id, '❗️ Не получилось отменить аккаунт, завершаю процесс...')
                break
        except PasswordRequired:
            Stamp(f'Account {i + 1} requires password', 'w')
            BOT.send_message(user_id, f'❌ Аккаунт {i + 1} требует пароль, перехожу к следующему...')
            continue
        except RecursionError:
            Stamp(f'Exiting because of recursion error', 'w')
            BOT.send_message(user_id, '❗️ Завершаю процесс покупки из-за рекурсивной ошибки...')
            break
        except Exception as e:
            Stamp(f'Error while adding accounts: {e}', 'e')
            BOT.send_message(user_id, f'❌ Произошла неизвестная ошибка при добавлении аккаунта {i + 1}, завершаю процесс...')
            break


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
                BOT.send_message(user_id, f'📱 Куплен номер {num}')
            else:
                Stamp(f'No "number" field in response <-> no available numbers in this region', 'e')
                BOT.send_message(user_id, '⛔️ Нет доступных номеров в этом регионе, '
                                                       'прекращаю процесс покупки...')
                raise
        else:
            Stamp(f'Failed to buy account: {response.text}', 'e')
            BOT.send_message(user_id, f'❌ Не удалось купить аккаунт, '
                                                   f'пробую ещё раз через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP)
            num, tzid = BuyAccount(user_id)
    return num, tzid


@ControlRecursion
def CancelNumber(user_id: int, num: str, tzid: str) -> None:
    try:
        response = get(URL_CANCEL, params={'apikey': TOKEN_SIM, 'tzid': tzid, 'ban': 1, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while cancelling number {num}: {e}', 'e')
        BOT.send_message(user_id, f'‼️ Не удалось связаться с сервером для отмены номера, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        CancelNumber(user_id, num, tzid)
    else:
        if str(response.status_code)[0] == '2' and str(response.json()['response']) == '1':
            Stamp(f'Successful cancelling of number {num}', 's')
            BOT.send_message(user_id, f'❇️ Номер {num} отменён')
        else:
            Stamp(f'Failed to cancel number {num}', 'w')
            BOT.send_message(user_id, f'ℹ️ Пока что не удалось отменить номер, '
                                                    f'пробую ещё раз через {LONG_SLEEP * 2} секунд...')
            Sleep(LONG_SLEEP * 2)
            CancelNumber(user_id, num, tzid)


def GetCodeFromSms(driver: Remote, user_id: int, num: str) -> str:
    start_time = time()
    while time() - start_time < MAX_WAIT_CODE:
        sms_dict = CheckAllSms(user_id)
        if sms_dict and num in sms_dict:
            Stamp(f'Found incoming sms for num {num}', 's')
            BOT.send_message(user_id, f'🔔 Нашёл код: {sms_dict[num]}')
            return sms_dict[num]
        Stamp(f'No incoming sms for {num} after {round(time() - start_time)} seconds of waiting', 'w')
        BOT.send_message(user_id, f'💤 Не вижу входящих сообщений после {round(time() - start_time)} секунд ожидания...')
        Sleep(LONG_SLEEP)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after code not received', 3)
    PressButton(driver, '//android.widget.TextView[@text="Edit"]', 'Another back after code not received', 3)
    raise ErrorAfterNumberInsertion


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
