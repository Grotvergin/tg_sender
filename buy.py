from telebot.types import Message
from source import (CANCEL_BTN, WELCOME_BTNS, BNT_NUM_OPERATION, BOT,
                    LONG_SLEEP, URL_BUY, MAX_ACCOUNTS_BUY, URL_CANCEL,
                    URL_SMS, URL_GET_TARIFFS, GET_API_CODE_BTN)
from secret import TOKEN_SIM
from common import ShowButtons, Sleep, Stamp, ControlRecursion
from info_senders import SendTariffInfo
from requests import get
from re import search, MULTILINE
from api import SendAPICode


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
