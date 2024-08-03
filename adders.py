from common import Sleep, Stamp
from source import ACCOUNTS, SHORT_SLEEP
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import SendReactionRequest
from telethon.errors import ReactionInvalidError
from telethon.tl.types import ReactionEmoji
from telethon.tl.functions.messages import GetMessagesViewsRequest, ImportChatInviteRequest
from telethon.errors import InviteRequestSentError
from asyncio import sleep as async_sleep


async def AddReactions(post_link: str, reactions_needed: int, acc_index: int, emoji: str) -> int:
    Stamp('Reaction adding procedure started', 'b')
    cnt_success_reactions = 0
    for i in range(reactions_needed):
        acc = ACCOUNTS[(acc_index + i) % len(ACCOUNTS)]
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
        Sleep(SHORT_SLEEP, 0.5)
    Stamp('Reaction adding procedure finished', 'b')
    return cnt_success_reactions


async def IncreasePostViews(post_link: str, views_needed: int, acc_index: int) -> int:
    Stamp('View increasing procedure started', 'b')
    cnt_success_views = 0
    for i in range(views_needed):
        acc = ACCOUNTS[(acc_index + i) % len(ACCOUNTS)]
        try:
            await acc(GetMessagesViewsRequest(peer=post_link.split('/')[0], id=[int(post_link.split('/')[1])], increment=True))
            cnt_success_views += 1
            Stamp(f"Viewed post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
        except Exception as e:
            Stamp(f"Failed to view post {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
        Sleep(SHORT_SLEEP, 0.5)
    Stamp('View increasing procedure finished', 'b')
    return cnt_success_views


async def PerformSubscription(link: str, amount: int, channel_type: str, acc_index: int) -> int:
    Stamp('Subscription procedure started', 'b')
    cnt_success_subs = 0
    for i in range(amount):
        acc = ACCOUNTS[(acc_index + i) % len(ACCOUNTS)]
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
        except Exception as e:
            Stamp(f"Failed to subscribe {acc.session.filename.split('_')[-1]} to {link}: {e}", 'e')
        Sleep(SHORT_SLEEP, 0.5)
    Stamp('Subscription procedure finished', 'b')
    return cnt_success_subs


async def RepostMessage(post_link: str, reposts_needed: int, acc_index: int) -> int:
    Stamp('Reposting procedure started', 'b')
    cnt_success_reposts = 0
    for i in range(reposts_needed):
        acc = ACCOUNTS[(acc_index + i) % len(ACCOUNTS)]
        try:
            entity = await acc.get_entity(post_link.split('/')[0])
            message_id = int(post_link.split('/')[1])
            await acc.forward_messages('me', message_id, entity)
            cnt_success_reposts += 1
            Stamp(f"Reposted post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
        except Exception as e:
            Stamp(f"Failed to repost {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
        await async_sleep(SHORT_SLEEP)
    Stamp('Reposting procedure finished', 'b')
    return cnt_success_reposts
