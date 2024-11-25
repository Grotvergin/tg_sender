import source
from source import (MAX_WAIT_CODE, SHORT_SLEEP, BOT,
                    LEFT_CORNER, RIGHT_CORNER, WELCOME_BTNS, SKIP_CODE)
from common import (Stamp, SkippedCodeInsertion, GetSector,
                    Sleep, ShowButtons, BuildService, ParseAccountRow)
from secret import SHEET_ID, SHEET_NAME
# ---
from asyncio import sleep as async_sleep
from os import getcwd
from os.path import join
from time import time, sleep
from traceback import format_exc
# ---
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.errors.rpcerrorlist import PhoneCodeExpiredError


def WaitForCode(max_wait_time: int) -> int | None:
    start = time()
    Stamp('Start of waiting for code', 'i')
    while not source.CODE:
        sleep(1)
        if (time() - start) > max_wait_time:
            Stamp('Code waiting timeout', 'w')
            return
    Stamp('Code received', 's')
    code = source.CODE
    source.CODE = None
    return code


async def CheckRefreshAuth() -> None:
    while True:
        if source.ADMIN_CHAT_ID:
            Stamp('Admin chat ID is set, authorizing accounts', 'i')
            await AuthorizeAccounts()
            source.ADMIN_CHAT_ID = None
        await async_sleep(SHORT_SLEEP)


def AuthCallback(number: str, user_id: int, max_wait_time: int) -> int:
    ShowButtons(user_id, SKIP_CODE, f'❗️Введите код для {number} в течение {max_wait_time} секунд:')
    code = WaitForCode(max_wait_time)
    if not code:
        raise TimeoutError('Too long code waiting')
    elif code == SKIP_CODE:
        raise SkippedCodeInsertion
    return int(code)


async def AuthorizeAccounts() -> None:
    Stamp('Authorization procedure started', 'b')
    try:
        BOT.send_message(source.ADMIN_CHAT_ID, '🔸Начата процедура авторизации...\n')
        data = GetSector(LEFT_CORNER, RIGHT_CORNER, BuildService(), SHEET_NAME, SHEET_ID)
        this_run_auth = [client.session.filename for client in source.ACCOUNTS]
        for index, account in enumerate(data):
            try:
                num, api_id, api_hash, password_tg, ip, port, login, password_proxy = ParseAccountRow(account)
            except IndexError:
                Stamp(f'Invalid account data: {account}', 'e')
                BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Неверные данные для аккаунта в строке {index + 2}!')
                continue
            session = join(getcwd(), 'sessions', f'{num}')
            if session + '.session' in this_run_auth:
                Stamp(f'Account {num} already authorized', 's')
                continue
            else:
                Stamp(f'Processing account {num}', 'i')
                client = TelegramClient(session, api_id, api_hash, proxy=(2, ip, port, True, login, password_proxy))
                try:
                    await client.start(phone=num, password=password_tg, code_callback=lambda: AuthCallback(num, source.ADMIN_CHAT_ID, MAX_WAIT_CODE))
                    source.ACCOUNTS.append(client)
                    Stamp(f'Account {num} authorized', 's')
                    BOT.send_message(source.ADMIN_CHAT_ID, f'✅ Аккаунт {num} авторизован')
                    Sleep(SHORT_SLEEP, 0.5)
                except PhoneCodeInvalidError:
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Неверный код для номера {num}.')
                    Stamp(f'Invalid code for {num}', 'e')
                    continue
                except PhoneCodeExpiredError:
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Истекло время действия кода для номера {num}.')
                    Stamp(f'Code expired for {num}', 'e')
                    continue
                except SessionPasswordNeededError:
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❗️Требуется двухфакторная аутентификация для номера {num}.')
                    Stamp(f'2FA needed for {num}', 'w')
                    continue
                except PhoneNumberInvalidError:
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Неверный номер телефона {num}.')
                    Stamp(f'Invalid phone number {num}', 'e')
                    continue
                except SkippedCodeInsertion:
                    Stamp(f'Skipping code insertion for {num}', 'w')
                    BOT.send_message(source.ADMIN_CHAT_ID, f'👌 Пропускаем аккаунт {num}...')
                    continue
                except TimeoutError:
                    Stamp('Too long code waiting', 'w')
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Превышено время ожидания кода для {num}!')
                    continue
                except Exception as e:
                    Stamp(f'Error while starting client for {num}: {e}, {format_exc()}', 'e')
                    BOT.send_message(source.ADMIN_CHAT_ID, f'❌ Ошибка при старте клиента для {num}: {str(e)}')
                    continue
        BOT.send_message(source.ADMIN_CHAT_ID, f'🔹Процедура завершена, авторизовано {len(source.ACCOUNTS)} аккаунтов\n')
        ShowButtons(source.ADMIN_CHAT_ID, WELCOME_BTNS, '❔ Выберите действие:')
    except Exception as e:
        Stamp(f'Unknown exception in authorization procedure: {e}', 'w')
    Stamp('All accounts authorized', 'b')
