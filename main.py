from asyncio import get_event_loop, gather, create_task
from traceback import format_exc
from threading import Thread
from telebot.types import Message
from common import ShowButtons, Stamp
from file import LoadRequestsFromFile
from source import (BOT, WELCOME_BTNS, SINGLE_BTNS, AUTO_CHOICE,
                    CANCEL_BTN, ACCOUNTS, FILE_FINISHED,
                    FILE_AUTO_VIEWS, FILE_AUTO_REPS)
from auth import CheckRefreshAuth
from processors import ProcessRequests
from event_handler import RefreshEventHandler
from buy import AddAccounts
from single_data_accept import SingleChoice
from auto_data_accept import AutomaticChoice
from asyncio import run
from info_senders import ListAccountNumbers


async def Main() -> None:
    global FINISHED_REQS, AUTO_VIEWS_DICT, AUTO_REPS_DICT
    FINISHED_REQS = LoadRequestsFromFile('finished', FILE_FINISHED)
    AUTO_VIEWS_DICT = LoadRequestsFromFile('automatic views', FILE_AUTO_VIEWS)
    AUTO_REPS_DICT = LoadRequestsFromFile('automatic reposts', FILE_AUTO_REPS)
    loop = get_event_loop()
    refresh_task = create_task(RefreshEventHandler())
    process_task = create_task(ProcessRequests())
    auth_task = create_task(CheckRefreshAuth())
    try:
        await gather(refresh_task, process_task, auth_task)
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
    global CODE, ADMIN_CHAT_ID
    Stamp(f'User {message.from_user.id} requested {message.text}', 'i')
    if message.text == '/start':
        BOT.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, AUTO_CHOICE, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChoice)
    elif message.text == WELCOME_BTNS[2]:
        ADMIN_CHAT_ID = message.from_user.id
    elif message.text == WELCOME_BTNS[3]:
        BOT.send_message(message.from_user.id, f'👁 Сейчас доступно {len(ACCOUNTS)} аккаунтов:\n{ListAccountNumbers()}')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите количество аккаунтов:')
        BOT.register_next_step_handler(message, AddAccounts)
    elif message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text.isdigit() and len(message.text) == 5 or message.text == '-':
        Stamp(f'ID of code var is {id(CODE)} in MessageAccept', 'i')
        CODE = message.text
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Thread(target=BotPolling, daemon=True).start()
    run(Main())
