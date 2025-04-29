import source
from source import (SINGLE_BTNS, CANCEL_BTN, WELCOME_BTNS, NUMBER_LAST_FIN,
                    LINK_FORMAT, TIME_FORMAT, MAX_MINS, FILE_FINISHED, BOT, FILE_ACTIVE, TIMEOUT_CHECK_AVAILABLE)
from common import ShowButtons, Stamp
from info_senders import SendRequests
from file import LoadRequestsFromFile, SaveRequestsToFile, updateDailyStats
from deletion import DeleteSingleRequest
# ---
from re import match
from random import randint
from datetime import datetime, timedelta
from time import sleep
# ---
from telebot.types import Message
from emoji import EMOJI_DATA


def SingleChoice(message: Message) -> None:
    if message.text == SINGLE_BTNS[0]:
        SendRequests(message, source.REQS_QUEUE)
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == SINGLE_BTNS[1]:
        reqs = LoadRequestsFromFile('finished', FILE_FINISHED)
        SendRequests(message, reqs, amount=NUMBER_LAST_FIN)
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == SINGLE_BTNS[2]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал (https://t.me/name_or_hash или @name):')
        BOT.register_next_step_handler(message, ChannelSub)
    elif message.text == SINGLE_BTNS[3]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Просмотры')
    elif message.text == SINGLE_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Репосты')
    elif message.text == SINGLE_BTNS[5]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку так, как она указана в выводе активных заявок:')
        BOT.register_next_step_handler(message, DeleteSingleRequest, SingleChoice)
    elif message.text == SINGLE_BTNS[6]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте эмодзи:')
        BOT.register_next_step_handler(message, AcceptEmoji)
    elif message.text == SINGLE_BTNS[-1]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)


def RequestPeriod(message: Message) -> None:
    Stamp('Time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                source.CUR_REQ['start'] = datetime.now().strftime(TIME_FORMAT)
                source.CUR_REQ['finish'] = (datetime.now() + timedelta(minutes=int(message.text))).strftime(TIME_FORMAT)
                source.CUR_REQ['cur_acc_index'] = randint(0, len(source.ACCOUNTS) - 1)
                source.REQS_QUEUE.append(source.CUR_REQ)
                SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)
                BOT.send_message(message.from_user.id, "🆗 Заявка принята. Начинаю выполнение заявки...")
                updateDailyStats('extra')
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, RequestPeriod)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, RequestPeriod)


def NumberInsertingProcedure(message: Message) -> None:
    Stamp('Number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(source.ACCOUNTS):
                source.CUR_REQ['planned'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), "
                                                 "в течение которого будет выполняться заявка:")
                BOT.register_next_step_handler(message, RequestPeriod)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, NumberInsertingProcedure)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def ChannelSub(message: Message) -> None:
    Stamp('Channel link inserting procedure', 'i')
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name_or_hash или @name)")
        BOT.register_next_step_handler(message, ChannelSub)
    else:
        source.CUR_REQ = {'order_type': 'Подписка', 'initiator': f'{message.from_user.username} – {message.from_user.id}'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            source.CUR_REQ['channel_type'] = 'public'
            cut_link = cut_link[1:]
        elif cut_link[0] == '+':
            cut_link = cut_link[1:]
            source.CUR_REQ['channel_type'] = 'private'
        else:
            source.CUR_REQ['channel_type'] = 'public'
        source.CUR_REQ['link'] = cut_link
        source.CHECK_CHANNEL_LINK = message.text.strip()
        BOT.send_message(message.from_user.id, f'🕹 Проверяю доступное количество подписок, это займет некоторое время, вплоть до {TIMEOUT_CHECK_AVAILABLE} секунд')
        for _ in range(TIMEOUT_CHECK_AVAILABLE):
            if source.CHECKED_AVAILABLE_COUNT is not None:
                available = source.CHECKED_AVAILABLE_COUNT
                source.CHECKED_AVAILABLE_COUNT = None
                break
            sleep(1)
        else:
            available = 0
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество подписок'
                                         f' (реально доступно {available} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def AcceptEmoji(message: Message) -> None:
    Stamp('Emoji inserting procedure', 'i')
    if message.text not in EMOJI_DATA:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Вы ввели не эмодзи. Пожалуйста, введите только эмодзи")
            BOT.register_next_step_handler(message, AcceptEmoji)
    else:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Реакции', message.text)


def AcceptPost(message: Message, order_type: str, emoji: str = None) -> None:
    Stamp('Post link inserting procedure', 'i')
    if not match(LINK_FORMAT, message.text):
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Ссылка на пост не похожа на корректную. "
                                             "Пожалуйста, проверьте формат ссылки (https://t.me/name/post_id)")
            BOT.register_next_step_handler(message, AcceptPost, order_type)
    else:
        cut_link = '/'.join(message.text.split('/')[-2:])
        source.CUR_REQ = {'order_type': order_type, 'initiator': f'{message.from_user.username} – {message.from_user.id}', 'link': cut_link}
        if emoji:
            source.CUR_REQ['emoji'] = emoji
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество (доступно {len(source.ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def doRebrand(message):
    try:
        user_id = message.from_user.id
        parts = message.text.strip().split()
        if len(parts) != 2:
            BOT.send_message(user_id, '❌ Формат должен быть: old new. Попробуйте снова.')
            BOT.register_next_step_handler(message, doRebrand)
            return

        old_name, new_name = parts
        replaced = False

        dicts_list = [
            {'dict': source.AUTO_VIEWS_DICT, 'order_type': 'Просмотры', 'file': source.FILE_AUTO_VIEWS, 'desc': 'automatic views'},
            {'dict': source.AUTO_REPS_DICT, 'order_type': 'Репосты', 'file': source.FILE_AUTO_REPS, 'desc': 'automatic reposts'},
            {'dict': source.AUTO_REAC_DICT, 'order_type': 'Реакции', 'file': source.FILE_AUTO_REAC, 'desc': 'automatic reactions'},
        ]

        for d in dicts_list:
            data_dict = d['dict']
            if old_name in data_dict:
                data_dict[new_name] = data_dict.pop(old_name)
                SaveRequestsToFile(data_dict, d['desc'], d['file'])
                replaced = True
                BOT.send_message(user_id, f"🔁 {d['order_type']}: переименовано {old_name} → {new_name}")

        if not replaced:
            BOT.send_message(user_id, f"❗ Канал {old_name} не найден ни в одном из автоматических словарей.")
        else:
            BOT.send_message(user_id, "✅ Переименование завершено.")

    except Exception as e:
        Stamp(f'Ошибка в doRebrand: {e}', 'e')
        BOT.send_message(message.from_user.id, '⚠️ Произошла ошибка при переименовании. Попробуйте ещё раз.')
