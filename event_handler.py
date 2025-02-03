import source
from file import SaveRequestsToFile
from adders import PerformSubscription
from secret import MY_TG_ID
from source import (LONG_SLEEP, TIME_FORMAT, BOT, FILE_ACTIVE,
                    LINK_DECREASE_RATIO, LIMIT_DIALOGS, ALL_REACTIONS)
from common import Stamp, AsyncSleep
# ---
from re import compile
from random import randint, sample, uniform
from datetime import datetime, timedelta
# ---
from telethon.tl.functions.messages import GetDialogsRequest, GetAvailableReactionsRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerEmpty, Channel
from telethon.sync import TelegramClient
from telethon.events import NewMessage


async def RefreshEventHandler():
    while True:
        channels = (
                list(source.AUTO_VIEWS_DICT.keys()) +
                list(source.AUTO_REPS_DICT.keys()) +
                list(source.AUTO_REAC_DICT.keys())
        )
        if not source.ACCOUNTS:
            Stamp("No accounts available to set up event handler", 'w')
            BOT.send_message(MY_TG_ID, '💀 Нет аккаунтов для запуска EventHandler')
        elif not channels:
            Stamp("No need to set up event handler (no channels)", 'i')
            BOT.send_message(MY_TG_ID, '🥺 Нет необходимости запускать EventHandler')
        else:
            Stamp(f'Setting up event handler', 'i')
            already_subscribed = await GetSubscribedChannels(source.ACCOUNTS[0])
            list_for_subscription = [chan for chan in channels if chan not in already_subscribed]
            for chan in list_for_subscription:
                await PerformSubscription(chan, 1, 'public', 0)
            channel_ids = await GetChannelIDsByUsernames(source.ACCOUNTS[0], channels)
            source.ACCOUNTS[0].remove_event_handler(EventHandler)
            source.ACCOUNTS[0].add_event_handler(EventHandler, NewMessage(chats=channel_ids))
            Stamp("Set up", 's')
        await AsyncSleep(LONG_SLEEP * 2, 0.5)


async def createRequest(order_type, initiator, link, planned, time_limit, emoji=None):
    req = {
        'order_type': order_type,
        'initiator': initiator,
        'link': link,
        'start': datetime.now().strftime(TIME_FORMAT),
        'finish': (datetime.now() + timedelta(minutes=time_limit)).strftime(TIME_FORMAT),
        'planned': planned,
        'cur_acc_index': randint(0, len(source.ACCOUNTS) - 1)
    }
    if emoji:
        req['emoji'] = emoji
    source.REQS_QUEUE.append(req)
    SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)
    Stamp(f"Added request for {link}", 's')


async def handleReactions(channel_data, link, annual_amount, diff_reac_num):
    reac_list = await GetReactionsList(link.split('/')[0])
    if not reac_list:
        Stamp(f'No reactions for {link} available', 'w')
        return
    reaction_distribution = DistributeReactionsIntoEmojis(diff_reac_num, annual_amount, reac_list)
    for emoji, count in reaction_distribution.items():
        await createRequest(
            order_type='Реакции',
            initiator=f'Автоматическая от {channel_data["initiator"]}',
            link=link,
            planned=count,
            time_limit=channel_data['time_limit'],
            emoji=emoji
        )


async def EventHandler(event: NewMessage.Event):
    Stamp(f'Trying to add automatic request for channel {event.chat.username}', 'i')

    dicts_list = [
        {'dict': source.AUTO_VIEWS_DICT, 'order_type': 'Просмотры'},
        {'dict': source.AUTO_REPS_DICT, 'order_type': 'Репосты'},
        {'dict': source.AUTO_REAC_DICT, 'order_type': 'Реакции'}
    ]

    for item in dicts_list:
        dict_name, order_type = item['dict'], item['order_type']

        for channel_name, value in dict_name.items():
            if event.chat.username == channel_name:
                annual_amount = value['annual']
                diff_reac_num = randint(4, 7)
                Stamp(f'Annual amount before decision = {annual_amount}', 'i')
                if NeedToDecrease(event.message.text, channel_name):
                    if order_type in ('Репосты', 'Реакции'):
                        annual_amount = int(float(annual_amount) / LINK_DECREASE_RATIO)
                        Stamp(f'DECREASING! Now annual = {annual_amount}', 'w')
                    if order_type == 'Реакции':
                        diff_reac_num = randint(2, 4)
                Stamp(f'Annual amount after decision = {annual_amount}', 'i')
                rand_amount = randint(
                    int((1 - (float(value['spread']) / 100)) * annual_amount),
                    int((1 + (float(value['spread']) / 100)) * annual_amount)
                )
                rand_amount = max(1, min(rand_amount, len(source.ACCOUNTS)))
                link = f'{channel_name}/{event.message.id}'
                if order_type == 'Реакции':
                    await handleReactions(value, link, annual_amount, diff_reac_num)
                else:
                    await createRequest(
                        order_type=order_type,
                        initiator=f'Автоматическая от {value["initiator"]}',
                        link=link,
                        planned=rand_amount,
                        time_limit=value['time_limit']
                    )


def DistributeReactionsIntoEmojis(diff_reac_num, annual_amount, reac_list):
    if diff_reac_num > len(reac_list):
        diff_reac_num = len(reac_list)
    chosen_reactions = sample(reac_list, diff_reac_num)
    dominant_share = uniform(0.4, 0.7)
    remaining_share = 1 - dominant_share
    num_remaining = len(chosen_reactions) - 1
    random_shares = [uniform(1, remaining_share) for _ in range(num_remaining)]
    sum_random_shares = sum(random_shares)
    normalized_shares = [share * (remaining_share / sum_random_shares) for share in random_shares]
    shares = [dominant_share] + normalized_shares
    reaction_distribution = {}
    for reaction, share in zip(chosen_reactions, shares):
        reaction_distribution[reaction] = round(share * annual_amount)
    difference = annual_amount - sum(reaction_distribution.values())
    if difference != 0:
        reaction_distribution[chosen_reactions[0]] += difference
    return reaction_distribution


async def GetReactionsList(channel_link):
    channel = await source.ACCOUNTS[0].get_entity(channel_link)
    full_chat = await source.ACCOUNTS[0](GetFullChannelRequest(channel))
    result = full_chat.full_chat.available_reactions

    if not result:
        return []

    if hasattr(result, 'reactions'):
        reac_list = [reaction.emoticon for reaction in result.reactions if hasattr(reaction, 'emoticon')]
    else:
        reac_list = ALL_REACTIONS

    return reac_list


def NeedToDecrease(message_text: str, channel_name: str) -> bool:
    http_link = compile(r'https?://[^\s]+')
    dog_link = compile(r'@[\w]+')
    message_text = message_text.lower()
    channel_name = channel_name.lower()
    if http_link.search(message_text) or dog_link.search(message_text):
        Stamp('Found some link in post', 'i')
        if any(f'{url}{channel_name}' in message_text for url in [f'@', 'https://t.me/', 'http://t.me/']):
            Stamp('Link points to the same channel', 'w')
            return False
        Stamp('Link points to different channel', 'i')
        return True
    Stamp('No link found', 'i')
    return False


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
