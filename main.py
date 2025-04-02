import source
from common import ShowButtons, Stamp
from file import LoadRequestsFromFile
from source import (BOT, WELCOME_BTNS, SINGLE_BTNS, AUTO_CHOICE,
                    CANCEL_BTN, FILE_FINISHED, FILE_ACTIVE,
                    FILE_AUTO_VIEWS, FILE_AUTO_REPS, USER_RESPONSES, SKIP_CODE,
                    FILE_AUTO_REAC, AUTHORIZED_USERS_FILE)
from secret import SECRET_CODE
from json import dump, load
from auth import CheckRefreshAuth
from processors import ProcessRequests
from event_handler import RefreshEventHandler, CheckManualHandler, ManualEventAcceptLink
from buy import AddAccounts, CheckRefreshBuy
from single_data_accept import SingleChoice, doRebrand
from auto_data_accept import AutomaticChoice
from info_senders import SendAccountNumbers
from os.path import exists
# ---
from asyncio import get_event_loop, gather, create_task, run
from traceback import format_exc
from threading import Thread
# ---
from telebot.types import Message


def load_authorized_users() -> set:
    """Загружает список авторизованных пользователей из файла."""
    if exists(AUTHORIZED_USERS_FILE):
        with open(AUTHORIZED_USERS_FILE, "r") as f:
            return set(load(f))
    return set()


def save_authorized_users(users: set) -> None:
    """Сохраняет список авторизованных пользователей в файл."""
    with open(AUTHORIZED_USERS_FILE, "w") as f:
        dump(list(users), f)


async def Main() -> None:
    source.REQS_QUEUE = LoadRequestsFromFile('active', FILE_ACTIVE)
    source.FINISHED_REQS = LoadRequestsFromFile('finished', FILE_FINISHED)
    source.AUTO_VIEWS_DICT = LoadRequestsFromFile('automatic views', FILE_AUTO_VIEWS)
    source.AUTO_REPS_DICT = LoadRequestsFromFile('automatic reposts', FILE_AUTO_REPS)
    source.AUTO_REAC_DICT = LoadRequestsFromFile('automatic reactions', FILE_AUTO_REAC)
    source.AUTHORIZED_USERS = load_authorized_users()

    loop = get_event_loop()
    try:
        await gather(
            create_task(CheckRefreshBuy()),
            create_task(ProcessRequests()),
            create_task(CheckRefreshAuth()),  # ✅ Запускается сразу
            create_task(CheckManualHandler()),
            create_task(RefreshEventHandler())  # ✅ Но внутри ждёт появления аккаунтов
        )
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(format_exc(), 'e')


@BOT.message_handler(commands=['start'])
def StartHandler(message: Message):
    user_id = message.from_user.id
    text_parts = message.text.split()

    if len(text_parts) == 2 and text_parts[1] == SECRET_CODE:
        if user_id not in source.AUTHORIZED_USERS:
            source.AUTHORIZED_USERS.add(user_id)
            save_authorized_users(source.AUTHORIZED_USERS)
            BOT.send_message(user_id, "✅ Вы успешно авторизованы! Добро пожаловать!")
        else:
            BOT.send_message(user_id, "🔓 Вы уже авторизованы.")
    else:
        BOT.send_message(user_id, "❌ Неверный или отсутствующий код доступа.")


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: Message) -> None:
    user_id = message.from_user.id
    Stamp(f'User {user_id} requested {message.text}', 'i')

    if user_id not in source.AUTHORIZED_USERS:
        BOT.send_message(user_id, "⛔️ Нет доступа. Используйте ссылку с кодом для входа.")
        return

    if user_id in USER_RESPONSES:
        USER_RESPONSES[user_id].put_nowait(message.text)
        return
    if message.text == WELCOME_BTNS[0]:
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, AUTO_CHOICE, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChoice)
    elif message.text == WELCOME_BTNS[2]:
        Stamp(f'Setting ADMIN_CHAT_ID = {user_id}', 'w')
        source.ADMIN_CHAT_ID = user_id
    elif message.text == WELCOME_BTNS[3]:
        SendAccountNumbers(user_id)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите количество аккаунтов:')
        BOT.register_next_step_handler(message, AddAccounts)
    elif message.text == WELCOME_BTNS[5]:
        source.BUYING_INFO = {'user_id': message.from_user.id, 'req_quantity': 1, 'country_code': 0, 'is_buy': False}
    elif message.text == WELCOME_BTNS[6]:
        BOT.send_message(user_id, '➡️ Введите ссылку на пост в формате https://t.me/channel_name/123')
        BOT.register_next_step_handler(message, ManualEventAcceptLink)
    elif message.text == WELCOME_BTNS[7]:
        BOT.send_message(user_id, '📐 Введите старое и новое название в формате old new')
        BOT.register_next_step_handler(message, doRebrand)
    elif message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text.isdigit() and len(message.text) == 5 or message.text == SKIP_CODE[0]:
        source.CODE = message.text
    else:
        BOT.send_message(user_id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Thread(target=BotPolling, daemon=True).start()
    run(Main())
