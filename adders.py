import source
from common import Stamp
from source import ACCOUNTS
# ---
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import SendReactionRequest, GetMessagesViewsRequest, ImportChatInviteRequest
from telethon.errors import (ReactionInvalidError, MessageIdInvalidError, ChannelPrivateError, ChatIdInvalidError,
                             PeerIdInvalidError, ChannelInvalidError, InviteHashInvalidError)
from telethon.tl.types import ReactionEmoji
from telethon.errors import InviteRequestSentError
from telethon.errors.rpcerrorlist import FloodWaitError


async def AddReactions(post_link: str, reactions_needed: int, acc_index: int, emoji: str) -> int:
    cnt_success_reactions = 0
    if len(ACCOUNTS) == 0:
        Stamp('No available accounts', 'e')
        return cnt_success_reactions
    for i in range(reactions_needed):
        index = (acc_index + i) % len(ACCOUNTS)
        acc = ACCOUNTS[index]
        async with source.LOCKS[index]:
            try:
                entity = await acc.get_entity(post_link.split('/')[0])
                message_id = int(post_link.split('/')[1])
                await acc(SendReactionRequest(
                    peer=entity,
                    msg_id=message_id,
                    reaction=[ReactionEmoji(emoticon=emoji)]
                ))
                cnt_success_reactions += 1
                Stamp(f"Added reaction to post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
            except ReactionInvalidError as e:
                raise e
            except Exception as e:
                Stamp(f"Failed to add reaction to {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
    return cnt_success_reactions


async def IncreasePostViews(post_link: str, views_needed: int, acc_index: int) -> int:
    cnt_success_views = 0
    if len(ACCOUNTS) == 0:
        Stamp('No available accounts', 'e')
        return cnt_success_views
    for i in range(views_needed):
        index = (acc_index + i) % len(ACCOUNTS)
        acc = ACCOUNTS[index]
        async with source.LOCKS[index]:
            try:
                await acc(GetMessagesViewsRequest(peer=post_link.split('/')[0], id=[int(post_link.split('/')[1])], increment=True))
                cnt_success_views += 1
                Stamp(f"Viewed post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
            except (ChannelPrivateError, ChatIdInvalidError, PeerIdInvalidError) as e:
                raise e
            except Exception as e:
                Stamp(f"Failed to view post {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
    return cnt_success_views


async def PerformSubscription(link: str, amount: int, channel_type: str, acc_index: int) -> int:
    cnt_success_subs = 0
    if len(ACCOUNTS) == 0:
        Stamp('No available accounts', 'e')
        return cnt_success_subs
    for i in range(amount):
        index = (acc_index + i) % len(ACCOUNTS)
        acc = ACCOUNTS[index]
        async with source.LOCKS[index]:
            try:
                if channel_type == 'public':
                    channel = await acc.get_entity(link)
                    await acc(JoinChannelRequest(channel))
                else:
                    try:
                        await acc(ImportChatInviteRequest(link))
                    except InviteRequestSentError:
                        Stamp('Caught InviteSendRequest error, continuing', 'i')
                Stamp(f"Subscribed {acc.session.filename.split('_')[-1]} to {link}", 's')
                cnt_success_subs += 1
            except (ChannelInvalidError, InviteHashInvalidError) as e:
                raise e
            except FloodWaitError as e:
                Stamp(f'Flood {acc.session.filename.split('_')[-1]}, wait {e.seconds}', 'e')
            except Exception as e:
                Stamp(f"Failed to subscribe {acc.session.filename.split('_')[-1]} to {link}: {e}", 'e')
    return cnt_success_subs


async def RepostMessage(post_link: str, reposts_needed: int, acc_index: int) -> int:
    cnt_success_reposts = 0
    if len(ACCOUNTS) == 0:
        Stamp('No available accounts', 'e')
        return cnt_success_reposts
    for i in range(reposts_needed):
        index = (acc_index + i) % len(ACCOUNTS)
        acc = ACCOUNTS[index]
        async with source.LOCKS[index]:
            try:
                entity = await acc.get_entity(post_link.split('/')[0])
                message_id = int(post_link.split('/')[1])
                await acc.forward_messages('me', message_id, entity)
                cnt_success_reposts += 1
                Stamp(f"Reposted post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
            except MessageIdInvalidError as e:
                raise e
            except Exception as e:
                Stamp(f"Failed to repost {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
    return cnt_success_reposts
