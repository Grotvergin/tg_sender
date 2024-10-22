import source
from source import (SINGLE_BTNS, CANCEL_BTN, WELCOME_BTNS, NUMBER_LAST_FIN,
                    LINK_FORMAT, TIME_FORMAT, MAX_MINS, FILE_FINISHED, BOT, FILE_ACTIVE)
from common import ShowButtons, Stamp
from info_senders import SendRequests
from file import LoadRequestsFromFile, SaveRequestsToFile
from deletion import DeleteSingleRequest
# ---
from re import match
from random import randint
from datetime import datetime, timedelta
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
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество подписок'
                                         f'(доступно {len(source.ACCOUNTS)} аккаунтов):')
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
