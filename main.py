import source
from common import ShowButtons, Stamp
from file import LoadRequestsFromFile
from source import (BOT, WELCOME_BTNS, SINGLE_BTNS, AUTO_CHOICE,
                    CANCEL_BTN, FILE_FINISHED, FILE_ACTIVE,
                    FILE_AUTO_VIEWS, FILE_AUTO_REPS, USER_RESPONSES, SKIP_CODE, FILE_AUTO_REAC)
from auth import CheckRefreshAuth
from processors import ProcessRequests
from event_handler import RefreshEventHandler
from buy import AddAccounts, CheckRefreshBuy
from single_data_accept import SingleChoice
from auto_data_accept import AutomaticChoice
from info_senders import ListAccountNumbers
# ---
from asyncio import get_event_loop, gather, create_task, run
from traceback import format_exc
from threading import Thread
# ---
from telebot.types import Message


async def Main() -> None:
    source.REQS_QUEUE = LoadRequestsFromFile('active', FILE_ACTIVE)
    source.FINISHED_REQS = LoadRequestsFromFile('finished', FILE_FINISHED)
    source.AUTO_VIEWS_DICT = LoadRequestsFromFile('automatic views', FILE_AUTO_VIEWS)
    source.AUTO_REPS_DICT = LoadRequestsFromFile('automatic reposts', FILE_AUTO_REPS)
    source.AUTO_REAC_DICT = LoadRequestsFromFile('automatic reactions', FILE_AUTO_REAC)
    loop = get_event_loop()
    try:
        await gather(create_task(CheckRefreshBuy()),
                     create_task(ProcessRequests()),
                     create_task(CheckRefreshAuth()),
                     create_task(RefreshEventHandler()))
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(format_exc(), 'e')


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: Message) -> None:
    user_id = message.from_user.id
    Stamp(f'User {user_id} requested {message.text}', 'i')
    if user_id in USER_RESPONSES:
        USER_RESPONSES[user_id].put_nowait(message.text)
        return
    if message.text == '/start':
        BOT.send_message(user_id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, AUTO_CHOICE, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChoice)
    elif message.text == WELCOME_BTNS[2]:
        Stamp(f'Setting ADMIN_CHAT_ID = {user_id}', 'w')
        source.ADMIN_CHAT_ID = user_id
    elif message.text == WELCOME_BTNS[3]:
        BOT.send_message(user_id, f'👁 Доступно {len(source.ACCOUNTS)} аккаунтов:\n{ListAccountNumbers()}')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите количество аккаунтов:')
        BOT.register_next_step_handler(message, AddAccounts)
    elif message.text == WELCOME_BTNS[5]:
        source.BUYING_INFO = {'user_id': message.from_user.id, 'req_quantity': 1, 'country_code': 0, 'is_buy': False}
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
