import source
from source import BOT, WELCOME_BTNS, SINGLE_BTNS, FILE_ACTIVE, FILE_AUTO_VIEWS, FILE_AUTO_REPS, FILE_AUTO_REAC
from common import ShowButtons, Stamp
from file import SaveRequestsToFile
# ---
from typing import Callable
# ---
from telebot.types import Message


def DeleteSingleRequest(message: Message, clbk: Callable) -> None:
    cnt = 0
    for i, req in enumerate(source.REQS_QUEUE):
        if req['link'] == message.text:
            Stamp(f'Deleting request for {req["link"]}', 'i')
            del source.REQS_QUEUE[i]
            SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)
            cnt += 1
    if cnt == 0:
        Stamp('No deletions made', 'w')
        BOT.send_message(message.from_user.id, '🛑 Удалений не произошло!')
    else:
        Stamp(f'{cnt} requests were deleted', 's')
        BOT.send_message(message.from_user.id, f'✅ Было удалено {cnt} разовых заявок')
    ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
    BOT.register_next_step_handler(message, clbk)


def DeleteAutomaticRequest(message: Message, path: str, emoji: str = None) -> None:
    PATH_TO_DATA_MAP = {
        FILE_AUTO_VIEWS: (source.AUTO_VIEWS_DICT, 'automatic views'),
        FILE_AUTO_REPS: (source.AUTO_REPS_DICT, 'automatic reposts'),
        FILE_AUTO_REAC: (source.AUTO_REAC_DICT, 'automatic reactions'),
    }
    data_info = PATH_TO_DATA_MAP.get(path)
    if data_info:
        data_dict, description = data_info
        if emoji:
            key = message.text + '_' + emoji
        else:
            key = message.text
        if key in data_dict.keys():
            del data_dict[key]
            SaveRequestsToFile(data_dict, description, path)
            BOT.send_message(message.from_user.id, f'✅ Автоматическая заявка на {description} для канала {message.text} удалена')
        else:
            BOT.send_message(message.from_user.id, '❌ Не нашёл автоматической заявки на такой канал')
    else:
        BOT.send_message(message.from_user.id, '❌ Некорректный путь файла')
    ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
