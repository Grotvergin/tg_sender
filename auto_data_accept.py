import source
from source import (AUTO_BTNS, CANCEL_BTN, WELCOME_BTNS, AUTO_CHOICE, LINK_FORMAT,
                    MAX_MINS, TIME_FORMAT, BOT, FILE_AUTO_VIEWS, FILE_AUTO_REAC, FILE_AUTO_REPS)
from common import ShowButtons, Stamp
from file import SaveRequestsToFile
from deletion import DeleteAutomaticRequest
from info_senders import SendAutomaticRequests
# ---
from re import match
from datetime import datetime
# ---
from telebot.types import Message
from emoji import EMOJI_DATA


def AutomaticChoice(message: Message) -> None:
    if message.text == AUTO_CHOICE[0]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, FILE_AUTO_VIEWS)
    elif message.text == AUTO_CHOICE[1]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, FILE_AUTO_REPS)
    elif message.text == AUTO_CHOICE[2]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте эмодзи:')
        BOT.register_next_step_handler(message, AutomaticAcceptEmoji)
    elif message.text == AUTO_CHOICE[3]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def AutomaticAcceptEmoji(message: Message) -> None:
    Stamp('Emoji inserting procedure', 'i')
    if message.text not in EMOJI_DATA:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Вы ввели не эмодзи. Пожалуйста, введите только эмодзи")
            BOT.register_next_step_handler(message, AutomaticAcceptEmoji)
    else:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, FILE_AUTO_REAC)


def AutomaticChannelDispatcher(message: Message, file: str) -> None:
    if message.text == AUTO_BTNS[0]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал (https://t.me/name или @name):')
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    elif message.text == AUTO_BTNS[1]:
        BOT.send_message(message.from_user.id, '❔ Введите имя канала (name):')
        BOT.register_next_step_handler(message, DeleteAutomaticRequest, file)
    elif message.text == AUTO_BTNS[2]:
        FILE_TO_DATA_MAP = {
            source.FILE_AUTO_VIEWS: source.AUTO_VIEWS_DICT,
            source.FILE_AUTO_REPS: source.AUTO_REPS_DICT,
            source.FILE_AUTO_REAC: source.AUTO_REAC_DICT,
        }
        data = FILE_TO_DATA_MAP.get(file)
        SendAutomaticRequests(message, data)
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, file)
    elif message.text == AUTO_BTNS[3]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def AutomaticChannelAction(message: Message, file: str, emoji: str = None) -> None:
    Stamp('Automatic channel link inserting procedure', 'i')
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name или @name)")
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    else:
        source.CUR_REQ = {'initiator': f'{message.from_user.username} – {message.from_user.id}'}
        if emoji:
            source.CUR_REQ['emoji'] = emoji
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            cut_link = cut_link[1:]
        source.CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите количество аккаунтов, которые '
                                         f'будут автоматически совершать действие с новой публикацией '
                                         f'(доступно {len(source.ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def AutomaticNumberProcedure(message: Message, file: str) -> None:
    Stamp('Automatic number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(source.ACCOUNTS):
                source.CUR_REQ['annual'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), отведённый на действие")
                BOT.register_next_step_handler(message, AutomaticPeriod, file)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def AutomaticPeriod(message: Message, path: str) -> None:
    Stamp('Automatic time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                source.CUR_REQ['time_limit'] = int(message.text)
                BOT.send_message(message.from_user.id, '❔ Введите разброс (в %, от 0 до 100), с которым рассчитается количество:')
                BOT.register_next_step_handler(message, InsertSpread, path)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticPeriod, path)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticPeriod, path)


def InsertSpread(message: Message, path: str) -> None:
    Stamp('Automatic spread inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            return
        if not 0 <= int(message.text) < 100:
            ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
            BOT.register_next_step_handler(message, InsertSpread, path)
            return
        PATH_TO_DATA_MAP = {
            FILE_AUTO_VIEWS: (source.AUTO_VIEWS_DICT, 'automatic views', FILE_AUTO_VIEWS),
            FILE_AUTO_REPS: (source.AUTO_REPS_DICT, 'automatic reposts', FILE_AUTO_REPS),
            FILE_AUTO_REAC: (source.AUTO_REAC_DICT, 'automatic reactions', FILE_AUTO_REAC)
        }
        data_info = PATH_TO_DATA_MAP.get(path)
        if not data_info:
            BOT.send_message(message.from_user.id, '❌ Некорректный путь файла.')
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            return
        data_dict, description, file_name = data_info
        record = {
            'initiator': source.CUR_REQ['initiator'],
            'time_limit': source.CUR_REQ['time_limit'],
            'approved': datetime.now().strftime(TIME_FORMAT),
            'annual': source.CUR_REQ['annual'],
            'spread': int(message.text)
        }
        link = source.CUR_REQ['link']
        if 'emoji' in source.CUR_REQ:
            record['emoji'] = source.CUR_REQ['emoji']
            link += '_' + source.CUR_REQ['emoji']
        data_dict[link] = record
        SaveRequestsToFile(data_dict, description, file_name)
        BOT.send_message(message.from_user.id, f"🆗 Заявка принята. Буду следить за обновлениями в канале {source.CUR_REQ['link']}...")
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, InsertSpread, path)
