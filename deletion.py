from telebot.types import Message
from source import (BOT, REQS_QUEUE, AUTO_SUBS_DICT,
                    AUTO_REPS_DICT, WELCOME_BTNS, SINGLE_BTNS)
from common import ShowButtons, Stamp
from file import SaveRequestsToFile
from typing import Callable


def DeleteSingleRequest(message: Message, clbk: Callable) -> None:
    cnt = 0
    for i, req in enumerate(REQS_QUEUE):
        if req['link'] == message.text:
            Stamp(f'Deleting request for {req["link"]}', 'i')
            del REQS_QUEUE[i]
            cnt += 1
    if cnt == 0:
        Stamp('No deletions made', 'w')
        BOT.send_message(message.from_user.id, '🛑 Удалений не произошло!')
    else:
        Stamp(f'{cnt} requests were deleted', 's')
        BOT.send_message(message.from_user.id, f'✅ Было удалено {cnt} разовых заявок')
    ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
    BOT.register_next_step_handler(message, clbk)


def DeleteAutomaticRequest(message: Message, path: str) -> None:
    if message.text in AUTO_SUBS_DICT.keys() and path == 'auto_views.json':
        del AUTO_SUBS_DICT[message.text]
        SaveRequestsToFile(AUTO_SUBS_DICT, 'automatic subs', path)
        BOT.send_message(message.from_user.id, f'✅ Автоматическая заявка на просмотры для канала {message.text} удалена')
    elif message.text in AUTO_REPS_DICT.keys() and path == 'auto_reps.json':
        del AUTO_REPS_DICT[message.text]
        SaveRequestsToFile(AUTO_REPS_DICT, 'automatic reps', path)
        BOT.send_message(message.from_user.id, f'✅ Автоматическая заявка на репосты для канала {message.text} удалена')
    else:
        BOT.send_message(message.from_user.id, '❌ Не нашёл автоматической заявки на такой канал')
    ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
