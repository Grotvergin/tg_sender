from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel
from telethon.sync import TelegramClient
from telethon.events import NewMessage
from re import compile
from random import randint
from source import (LONG_SLEEP, TIME_FORMAT, REQS_QUEUE,
                    ACCOUNTS, AUTO_SUBS_DICT, AUTO_REPS_DICT,
                    BOT, LINK_DECREASE_RATIO, LIMIT_DIALOGS)
from common import Stamp, AsyncSleep
from datetime import datetime, timedelta
from adders import PerformSubscription


async def RefreshEventHandler():
    while True:
        channels = list(AUTO_SUBS_DICT.keys()) + list(AUTO_REPS_DICT.keys())
        if not ACCOUNTS:
            Stamp("No accounts available to set up event handler", 'w')
        elif not channels:
            Stamp("No need to set up event handler (no channels)", 'i')
        else:
            Stamp(f'Setting up event handler', 'i')
            already_subscribed = await GetSubscribedChannels(ACCOUNTS[0])
            list_for_subscription = [chan for chan in channels if chan not in already_subscribed]
            for chan in list_for_subscription:
                await PerformSubscription(chan, 1, 'public', 0)
            channel_ids = await GetChannelIDsByUsernames(ACCOUNTS[0], channels)
            ACCOUNTS[0].remove_event_handler(EventHandler)
            ACCOUNTS[0].add_event_handler(EventHandler, NewMessage(chats=channel_ids))
            Stamp("Set up", 's')
        await AsyncSleep(LONG_SLEEP * 3, 0.5)


async def EventHandler(event: NewMessage.Event):
    Stamp(f'Trying to add automatic request for channel {event.chat.username}', 'i')
    dicts_list = ({'dict': AUTO_SUBS_DICT, 'order_type': 'Просмотры'}, {'dict': AUTO_REPS_DICT, 'order_type': 'Репосты'})
    user_id = None
    for item in dicts_list:
        dict_name = item['dict']
        order_type = item['order_type']
        if event.chat.username in dict_name:
            if order_type == 'Репосты' and bool(compile(r'http?').search(event.message.message)):
                dict_name[event.chat.username]['annual'] = int(float(dict_name[event.chat.username]['annual']) / LINK_DECREASE_RATIO)
            rand_amount = randint(int((1 - (float(dict_name[event.chat.username]['spread']) / 100)) * dict_name[event.chat.username]['annual']),
                                  int((1 + (float(dict_name[event.chat.username]['spread']) / 100)) * dict_name[event.chat.username]['annual']))
            if rand_amount > len(ACCOUNTS):
                rand_amount = len(ACCOUNTS)
            REQS_QUEUE.append({'order_type': order_type,
                               'initiator': f'Автоматическая от {dict_name[event.chat.username]["initiator"]}',
                               'link': f'{event.chat.username}/{event.message.id}',
                               'start': datetime.now().strftime(TIME_FORMAT),
                               'finish': (datetime.now() + timedelta(minutes=dict_name[event.chat.username]['time_limit'])).strftime(TIME_FORMAT),
                               'planned': rand_amount,
                               'cur_acc_index': randint(0, len(ACCOUNTS) - 1)})
            user_id = dict_name[event.chat.username]['initiator'].split(' ')[-1]
    Stamp(f'Added automatic request for channel {event.chat.username}', 's')
    BOT.send_message(user_id, f'⚡️ Обнаружена новая публикация в канале {event.chat.username}, заявка создана')


async def GetChannelIDsByUsernames(account, requested_usernames: list[str]) -> list[int]:
    Stamp('Finding out ids for all channels for an account', 'i')
    result = await account(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=LIMIT_DIALOGS,
        hash=0
    ))
    ids = []
    for chat in result.chats:
        if isinstance(chat, Channel):
            chan_usernames = []
            if chat.username:
                chan_usernames.append(chat.username)
            elif chat.usernames:
                for name in chat.usernames:
                    chan_usernames.append(name.username)
            if any(username in requested_usernames for username in chan_usernames):
                ids.append(int(chat.id))
    return ids


async def GetSubscribedChannels(account: TelegramClient) -> list[str]:
    Stamp('Getting all channels', 'i')
    result = await account(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=1000,
        hash=0
    ))
    channels = []
    for chat in result.chats:
        if isinstance(chat, Channel):
            if chat.username:
                channels.append(chat.username)
            elif chat.usernames:
                for name in chat.usernames:
                    channels.append(name.username)
    return channels
