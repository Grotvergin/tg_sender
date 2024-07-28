from source import *


async def Main() -> None:
    global FINISHED_REQS, AUTO_SUBS_DICT, AUTO_REPS_DICT
    FINISHED_REQS = LoadRequestsFromFile('finished', 'finished.json')
    AUTO_SUBS_DICT = LoadRequestsFromFile('automatic subs', 'auto_views.json')
    AUTO_REPS_DICT = LoadRequestsFromFile('automatic reps', 'auto_reps.json')
    loop = get_event_loop()
    new_task = create_task(CheckNewAuth())
    refresh_task = create_task(RefreshEventHandler())
    process_task = create_task(ProcessRequests())
    auth_task = create_task(CheckRefreshAuth())
    try:
        await gather(refresh_task, process_task, auth_task, new_task)
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(format_exc(), 'e')


def WaitForCode() -> int | None:
    global CODE
    start = time()
    while not CODE:
        sleep(1)
        Stamp('Waiting for code', 'l')
        if (time() - start) > MAX_WAIT_CODE:
            return
    code = CODE
    CODE = None
    return code


async def CheckNewAuth() -> None:
    global NEW_ROW_TO_ADD
    while True:
        if NEW_ROW_TO_ADD:
            Stamp(f'New row to add is set, authorizing account on row {NEW_ROW_TO_ADD}', 'i')
            await AuthNewAccount(NEW_ROW_TO_ADD)
            NEW_ROW_TO_ADD = None
        await async_sleep(SHORT_SLEEP)


def GenerateRandomRussianName():
    first_names = ['Алексей', 'Андрей', 'Борис', 'Владимир', 'Георгий', 'Дмитрий', 'Евгений', 'Игорь', 'Константин', 'Максим']
    last_names = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Петров']
    return choice(first_names), choice(last_names)


def GenerateRandomDescription():
    descriptions = [
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
        'Интересуюсь искусством и культурой.',
        'Занимаюсь фотографией и видеосъемкой.'
    ]
    return choice(descriptions)


def GetRandomProfilePicture():
    response = get('https://source.unsplash.com/random/200x200')
    if response.status_code == 200:
        return response.content
    return None


async def AddRandomContact(client):
    random_contact = InputPhoneContact(
        client_id=randint(0, 999999),
        phone='+' + str(randint(10000000000, 99999999999)),
        first_name=GenerateRandomRussianName()[0],
        last_name=GenerateRandomRussianName()[1]
    )
    try:
        result = await client(ImportContactsRequest(
            contacts=[random_contact]
        ))
        if result.imported:
            input_user = result.imported[0].user_id
            await client(AddContactRequest(
                id=InputUser(input_user, 0),
                first_name=random_contact.first_name,
                last_name=random_contact.last_name,
                phone=random_contact.phone,
                add_phone_privacy_exception=False
            ))
    except Exception as e:
        Stamp(f'Failed to add contact: {e}', 'e')


# async def SetTwoFactorPassword(client, new_password: str):
#     try:
#         current_password = await client(GetPasswordRequest())
#         new_srp_password = compute_check(
#             current_password.new_algo, new_password
#         )
#
#         await client(UpdatePasswordSettingsRequest(
#             password=current_password.new_algo,
#             new_settings=types.account.PasswordInputSettings(
#                 new_algo=new_srp_password['algo'],
#                 new_password_hash=new_srp_password['hash'],
#                 hint='My password hint'
#             )
#         ))
#         Stamp(f'2FA password set successfully', 's')
#     except Exception as e:
#         Stamp(f'Error while setting 2FA password: {e}', 'e')


async def AuthNewAccount(row: int) -> None:
    data = GetSector(f'E{row}', f'H{row}', SERVICE, EXTRA_SHEET_NAME, SHEET_ID)[0]
    try:
        num, api_id, api_hash, password_tg, ip, port, login, password_proxy = ParseAccountRow(data)
    except IndexError:
        Stamp(f'Invalid account data in row {row}', 'e')
        BOT.send_message(NEW_CHAT_ID, f'❌ Неверные данные для аккаунта в строке {row}!')
        return
    tg_session = join(getcwd(), 'sessions', f'{num}')
    client = TelegramClient(tg_session, api_id, api_hash, proxy=(SOCKS5, ip, port, True, login, password_proxy))
    try:
        await client.start(phone=num, password=password_tg, code_callback=lambda: AuthCallback(num))
        Stamp(f'Account {num} authorized', 's')
        BOT.send_message(NEW_CHAT_ID, f'✅ Аккаунт {num} авторизован')
        first_name, last_name = GenerateRandomRussianName()
        await client(UpdateProfileRequest(first_name=first_name, last_name=last_name, about=GenerateRandomDescription()))
        profile_picture = GetRandomProfilePicture()
        if profile_picture:
            file = await client.upload_file(profile_picture)
            await client(UploadProfilePhotoRequest(file=file))
        await AddRandomContact(client)
        # await SetTwoFactorPassword(client, 'Arkana')
        Stamp('Changed all data for the account', 's')
        BOT.send_message(NEW_CHAT_ID, f'🖍 Изменил данные об аккаунте')
    except PhoneCodeInvalidError:
        BOT.send_message(NEW_CHAT_ID, f'❌ Неверный код для номера {num}.')
        Stamp(f'Invalid code for {num}', 'e')
    except PhoneCodeExpiredError:
        BOT.send_message(NEW_CHAT_ID, f'❌ Истекло время действия кода для номера {num}.')
        Stamp(f'Code expired for {num}', 'e')
    except SessionPasswordNeededError:
        BOT.send_message(NEW_CHAT_ID, f'❗️Требуется двухфакторная аутентификация для номера {num}.')
        Stamp(f'2FA needed for {num}', 'w')
    except PhoneNumberInvalidError:
        BOT.send_message(NEW_CHAT_ID, f'❌ Неверный номер телефона {num}.')
        Stamp(f'Invalid phone number {num}', 'e')
    except SkippedCodeInsertion:
        Stamp(f'Skipping code insertion for {num}', 'w')
        BOT.send_message(NEW_CHAT_ID, f'👌 Пропускаем аккаунт {num}...')
    except TimeoutError:
        Stamp('Too long code waiting', 'w')
        BOT.send_message(NEW_CHAT_ID, f'❌ Превышено время ожидания кода для {num}!')
    except Exception as e:
        Stamp(f'Error while starting client for {num}: {e}, {format_exc()}', 'e')
        BOT.send_message(NEW_CHAT_ID, f'❌ Ошибка при старте клиента для {num}: {str(e)}')


def ParseAccountRow(account: list) -> tuple:
    num = account[0]
    api_id = account[1]
    api_hash = account[2]
    password_tg = account[3] if account[3] != '-' else None
    ip = account[4]
    port = int(account[5])
    login = account[6]
    password_proxy = account[7]
    return num, api_id, api_hash, password_tg, ip, port, login, password_proxy


async def CheckRefreshAuth() -> None:
    global ADMIN_CHAT_ID
    while True:
        if ADMIN_CHAT_ID is not None:
            Stamp('Admin chat ID is set, authorizing accounts', 'i')
            await AuthorizeAccounts()
            ADMIN_CHAT_ID = None
        await async_sleep(SHORT_SLEEP)


def AuthCallback(number: str) -> int:
    BOT.send_message(ADMIN_CHAT_ID, f'❗️Введите код для {number} в течение {MAX_WAIT_CODE} секунд '
                                    f'(либо "-" для пропуска этого аккаунта):')
    code = WaitForCode()
    if not code:
        raise TimeoutError('Too long code waiting')
    elif code == '-':
        raise SkippedCodeInsertion
    return int(code)


async def AuthorizeAccounts() -> None:
    Stamp('Authorization procedure started', 'b')
    try:
        BOT.send_message(ADMIN_CHAT_ID, '🔸Начата процедура авторизации...\n')
        data = GetSector(LEFT_CORNER, RIGHT_CORNER, SERVICE, SHEET_NAME, SHEET_ID)
        this_run_auth = [client.session.filename for client in ACCOUNTS]
        for index, account in enumerate(data):
            try:
                num, api_id, api_hash, password_tg, ip, port, login, password_proxy = ParseAccountRow(account)
            except IndexError:
                Stamp(f'Invalid account data: {account}', 'e')
                BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверные данные для аккаунта в строке {index + 2}!')
                continue
            session = join(getcwd(), 'sessions', f'{num}')
            if session + '.session' in this_run_auth:
                Stamp(f'Account {num} already authorized', 's')
                continue
            else:
                Stamp(f'Processing account {num}', 'i')
                client = TelegramClient(session, api_id, api_hash, proxy=(SOCKS5, ip, port, True, login, password_proxy))
                try:
                    await client.start(phone=num, password=password_tg, code_callback=lambda: AuthCallback(num))
                    ACCOUNTS.append(client)
                    Stamp(f'Account {num} authorized', 's')
                    BOT.send_message(ADMIN_CHAT_ID, f'✅ Аккаунт {num} авторизован')
                    Sleep(SHORT_SLEEP, 0.5)
                except PhoneCodeInvalidError:
                    BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверный код для номера {num}.')
                    Stamp(f'Invalid code for {num}', 'e')
                    continue
                except PhoneCodeExpiredError:
                    BOT.send_message(ADMIN_CHAT_ID, f'❌ Истекло время действия кода для номера {num}.')
                    Stamp(f'Code expired for {num}', 'e')
                    continue
                except SessionPasswordNeededError:
                    BOT.send_message(ADMIN_CHAT_ID, f'❗️Требуется двухфакторная аутентификация для номера {num}.')
                    Stamp(f'2FA needed for {num}', 'w')
                    continue
                except PhoneNumberInvalidError:
                    BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверный номер телефона {num}.')
                    Stamp(f'Invalid phone number {num}', 'e')
                    continue
                except SkippedCodeInsertion:
                    Stamp(f'Skipping code insertion for {num}', 'w')
                    BOT.send_message(ADMIN_CHAT_ID, f'👌 Пропускаем аккаунт {num}...')
                    continue
                except TimeoutError:
                    Stamp('Too long code waiting', 'w')
                    BOT.send_message(ADMIN_CHAT_ID, f'❌ Превышено время ожидания кода для {num}!')
                    continue
                except Exception as e:
                    Stamp(f'Error while starting client for {num}: {e}, {format_exc()}', 'e')
                    BOT.send_message(ADMIN_CHAT_ID, f'❌ Ошибка при старте клиента для {num}: {str(e)}')
                    continue
        BOT.send_message(ADMIN_CHAT_ID, f'🔹Процедура завершена, авторизовано {len(ACCOUNTS)} аккаунтов\n')
        ShowButtons(ADMIN_CHAT_ID, WELCOME_BTNS, '❔ Выберите действие:')
    except Exception as e:
        Stamp(f'Unknown exception in authorization procedure: {e}', 'w')
    Stamp('All accounts authorized', 'b')


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
        await AsyncSleep(SHORT_SLEEP, 0.5)
    Stamp('Reposting procedure finished', 'b')
    return cnt_success_reposts


async def ProcessOrder(req: dict, to_add: int):
    if req['order_type'] == 'Подписка':
        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'], req['cur_acc_index'])
    elif req['order_type'] == 'Просмотры':
        cnt_success = await IncreasePostViews(req['link'], to_add, req['cur_acc_index'])
    elif req['order_type'] == 'Репосты':
        cnt_success = await RepostMessage(req['link'], to_add, req['cur_acc_index'])
    elif req['order_type'] == 'Реакции':
        try:
            cnt_success = await AddReactions(req['link'], to_add, req['cur_acc_index'], req['emoji'])
        except ReactionInvalidError as e:
            Stamp(f"Bad reaction {req['emoji']} for {req['link']}: {e}", 'e')
            BOT.send_message(req['initiator'].split(' ')[-1], f"⚠️ Запрошенная реакция {req['emoji']} недоступна для заявки {req['link']}, заявка снимается...")
            REQS_QUEUE.remove(req)
            return
    else:
        Stamp('Unknown order type', 'e')
        return
    req['cur_acc_index'] = (req['cur_acc_index'] + to_add) % len(ACCOUNTS)
    req['current'] = req.get('current', 0) + cnt_success


async def ProcessRequests() -> None:
    while True:
        Stamp('Pending requests', 'i')
        for req in REQS_QUEUE:
            finish = datetime.strptime(req['finish'], TIME_FORMAT)
            start = datetime.strptime(req['start'], TIME_FORMAT)
            now = datetime.now()

            if now < finish:
                duration = (finish - start).total_seconds()
                interval = duration / req['planned']
                elapsed = (now - start).total_seconds()
                expected = int(elapsed / interval)
                current = req.get('current', 0)
                to_add = expected - current
                if to_add > 0:
                    await ProcessOrder(req, to_add)
            else:
                if now < finish + timedelta(minutes=MAX_MINS_REQ) and req.get('current', 0) < req['planned']:
                    to_add = req['planned'] - req.get('current', 0)
                    await ProcessOrder(req, to_add)
                else:
                    if req.get('current', 0) < req['planned']:
                        message = f"⚠️ Заявка снята из-за истечения времени\n\n{PrintRequest(req)}"
                    else:
                        message = f"✅ Заявка выполнена\n\n{PrintRequest(req)}"

                    REQS_QUEUE.remove(req)
                    FINISHED_REQS.append(req)
                    SaveRequestsToFile(FINISHED_REQS, 'finished', 'finished.json')
                    user_id = req['initiator'].split(' ')[-1]
                    BOT.send_message(user_id, message, parse_mode='HTML')
        await AsyncSleep(LONG_SLEEP, 0.5)


async def RefreshEventHandler():
    while True:
        channels = list(AUTO_SUBS_DICT.keys()) + list(AUTO_REPS_DICT.keys())
        if not ACCOUNTS:
            Stamp("No accounts available to set up event handler", 'w')
        elif not channels:
            Stamp("No need to set up event handler (no channels)", 'i')
        else:
            Stamp(f'Setting up event handler with channels: {", ".join(channels)}', 'i')
            already_subscribed = await GetSubscribedChannels(ACCOUNTS[0])
            Stamp(f'Already subscribed channels include: {", ".join(already_subscribed)}', 'i')
            list_for_subscription = [chan for chan in channels if chan not in already_subscribed]
            Stamp(f'List for subscription includes: {", ".join(list_for_subscription)}', 'i')
            for chan in list_for_subscription:
                await PerformSubscription(chan, 1, 'public', 0)
            channel_ids = await GetChannelIDsByUsernames(ACCOUNTS[0], channels)
            ACCOUNTS[0].remove_event_handler(EventHandler)
            ACCOUNTS[0].add_event_handler(EventHandler, NewMessage(chats=channel_ids))
            Stamp("Event handler for new messages set up", 's')
        await AsyncSleep(LONG_SLEEP * 3, 0.5)


async def GetChannelIDsByUsernames(account, requested_usernames: list[str]) -> list[int]:
    Stamp('Trying to find out ids for all channels for an account', 'i')
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
    Stamp('Trying to get all channels for an account', 'i')
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


def ContainsLink(text: str) -> bool:
    url_pattern = compile(r'http[s]?')
    return bool(url_pattern.search(text))


async def EventHandler(event: NewMessage.Event):
    Stamp(f'Trying to add automatic request for channel {event.chat.username}', 'i')
    dicts_list = ({'dict': AUTO_SUBS_DICT, 'order_type': 'Просмотры'}, {'dict': AUTO_REPS_DICT, 'order_type': 'Репосты'})
    user_id = None
    for item in dicts_list:
        dict_name = item['dict']
        order_type = item['order_type']
        if event.chat.username in dict_name:
            if order_type == 'Репосты' and ContainsLink(event.message.message):
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
    BOT.send_message(user_id, f'⚡️ Обнаружена новая публикация в канале {event.chat.username}, заявка создана')
    Stamp(f'Added automatic request for channel {event.chat.username}', 's')


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
        global CUR_REQ
        cut_link = '/'.join(message.text.split('/')[-2:])
        CUR_REQ = {'order_type': order_type, 'initiator': f'{message.from_user.username} – {message.from_user.id}', 'link': cut_link}
        if emoji:
            CUR_REQ['emoji'] = emoji
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество (доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def AcceptEmoji(message: Message) -> None:
    Stamp('Emoji inserting procedure', 'i')
    if message.text not in lib_emoji.EMOJI_DATA:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Вы ввели не эмодзи. Пожалуйста, введите только эмодзи")
            BOT.register_next_step_handler(message, AcceptEmoji)
    else:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Реакции', message.text)


def ChannelSub(message: Message) -> None:
    Stamp('Channel link inserting procedure', 'i')
    global CUR_REQ
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name_or_hash или @name)")
        BOT.register_next_step_handler(message, ChannelSub)
    else:
        CUR_REQ = {'order_type': 'Подписка', 'initiator': f'{message.from_user.username} – {message.from_user.id}'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            CUR_REQ['channel_type'] = 'public'
            cut_link = cut_link[1:]
        elif cut_link[0] == '+':
            cut_link = cut_link[1:]
            CUR_REQ['channel_type'] = 'private'
        else:
            CUR_REQ['channel_type'] = 'public'
        CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество подписок'
                                         f'(доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def AutomaticChannelAction(message: Message, file: str) -> None:
    Stamp('Automatic channel link inserting procedure', 'i')
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name или @name)")
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    else:
        global CUR_REQ
        CUR_REQ = {'initiator': f'{message.from_user.username} – {message.from_user.id}'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            cut_link = cut_link[1:]
        CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите количество аккаунтов, которые '
                                         f'будут автоматически совершать действие с новой публикацией '
                                         f'(доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def AutomaticNumberProcedure(message: Message, file: str) -> None:
    Stamp('Automatic number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(ACCOUNTS):
                CUR_REQ['annual'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), отведённый на действие")
                BOT.register_next_step_handler(message, AutomaticPeriod, file)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def InsertSpread(message: Message, path: str) -> None:
    Stamp('Automatic spread inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 <= int(message.text) < 100:
                CUR_REQ['spread'] = int(message.text)
                CUR_REQ['approved'] = datetime.now().strftime(TIME_FORMAT)
                record = {'initiator': CUR_REQ['initiator'],
                          'time_limit': CUR_REQ['time_limit'],
                          'approved': CUR_REQ['approved'],
                          'annual': CUR_REQ['annual'],
                          'spread': CUR_REQ['spread']}
                if path == 'auto_views.json':
                    AUTO_SUBS_DICT[CUR_REQ['link']] = record
                    SaveRequestsToFile(AUTO_SUBS_DICT, 'automatic subs', 'auto_views.json')
                else:
                    AUTO_REPS_DICT[CUR_REQ['link']] = record
                    SaveRequestsToFile(AUTO_REPS_DICT, 'automatic reps', 'auto_reps.json')
                BOT.send_message(message.from_user.id, f"🆗 Заявка принята. Буду следить за обновлениями в канале {CUR_REQ['link']}...")
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, InsertSpread, path)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, InsertSpread, path)


def AutomaticPeriod(message: Message, path: str) -> None:
    Stamp('Automatic time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['time_limit'] = int(message.text)
                BOT.send_message(message.from_user.id, '❔ Введите разброс (в %, от 0 до 100), с которым рассчитается количество:')
                BOT.register_next_step_handler(message, InsertSpread, path)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticPeriod, path)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticPeriod, path)


def SaveRequestsToFile(requests: list | dict, msg: str, file: str) -> None:
    Stamp(f'Saving {msg} requests', 'i')
    with open(file, 'w', encoding='utf-8') as f:
        dump(requests, f, ensure_ascii=False, indent=4)


def LoadRequestsFromFile(msg: str, file: str) -> list | dict:
    Stamp(f'Trying to load {msg} requests', 'i')
    if exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            if getsize(file) > 0:
                return load(f)
            else:
                Stamp(f'File with {msg} requests is empty', 'w')
    else:
        Stamp(f'No file with {msg} requests found', 'w')
    return []


def RequestPeriod(message: Message) -> None:
    Stamp('Time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['start'] = datetime.now().strftime(TIME_FORMAT)
                CUR_REQ['finish'] = (datetime.now() + timedelta(minutes=int(message.text))).strftime(TIME_FORMAT)
                CUR_REQ['cur_acc_index'] = randint(0, len(ACCOUNTS) - 1)
                REQS_QUEUE.append(CUR_REQ)
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
            if 0 < int(message.text) <= len(ACCOUNTS):
                CUR_REQ['planned'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), "
                                                 "в течение которого будет выполняться заявка:")
                BOT.register_next_step_handler(message, RequestPeriod)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, NumberInsertingProcedure)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def SendActiveRequests(message: Message) -> None:
    if REQS_QUEUE:
        BOT.send_message(message.from_user.id, f' ⏳ Показываю {len(REQS_QUEUE)} активные заявки:')
        for req in REQS_QUEUE:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='HTML')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет активных заявок')


def PrintRequest(req: dict) -> str:
    return (f"<b>Начало</b>: {req['start']}\n"
            f"<b>Конец</b>: {req['finish']}\n"
            f"<b>Тип</b>: {req['order_type']}\n"
            f"<b>Желаемое</b>: {req['planned']}\n"
            f"<b>Выполненное</b>: {req.get('current', 0)}\n"
            f"<b>Ссылка</b>: {req['link']}\n"
            f"<b>Инициатор</b>: {req['initiator']}\n"
            f"<b>Индекс аккаунта</b>: {req.get('cur_acc_index', 'N/A')}\n"
            f"<b>Эмодзи</b>: {req.get('emoji', 'N/A')}")


def PrintAutomaticRequest(chan: str, data: dict) -> str:
    return (f"<b>Канал</b>: {chan}\n"
            f"<b>Инициатор</b>: {data[chan]['initiator']}\n"
            f"<b>Временной интервал</b>: {data[chan]['time_limit']}\n"
            f"<b>Создана</b>: {data[chan]['approved']}\n"
            f"<b>На публикацию</b>: {data[chan]['annual']}\n"
            f"<b>Разброс</b>: {data[chan]['spread']}%\n"
            f"<b>Эмодзи</b>: {data[chan].get('emoji', 'N/A')}")


def SendFinishedRequests(message: Message) -> None:
    global FINISHED_REQS
    FINISHED_REQS = LoadRequestsFromFile('finished', 'finished.json')
    if FINISHED_REQS:
        BOT.send_message(message.from_user.id, f' 📋 Показываю {NUMBER_LAST_FIN} выполненные заявки:')
        for req in FINISHED_REQS[-NUMBER_LAST_FIN:]:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='HTML')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет выполненных заявок')


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


def AutomaticChoice(message: Message) -> None:
    if message.text == AUTO_CHOICE[0]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, 'auto_views.json')
    elif message.text == AUTO_CHOICE[1]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, 'auto_reps.json')
    elif message.text == AUTO_CHOICE[2]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def AutomaticChannelDispatcher(message: Message, file: str) -> None:
    if message.text == AUTO_BTNS[0]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал, для которого будет создана'
                                         ' автоматическая заявка (https://t.me/name или @name):')
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    elif message.text == AUTO_BTNS[1]:
        BOT.send_message(message.from_user.id, '❔ Введите имя канала, для которого нужно отменить '
                                               'автоматическую заявку (name):')
        BOT.register_next_step_handler(message, DeleteAutomaticRequest, file)
    elif message.text == AUTO_BTNS[2]:
        data = AUTO_SUBS_DICT if file == 'auto_views.json' else AUTO_REPS_DICT
        if data.keys():
            for chan in data.keys():
                BOT.send_message(message.from_user.id, PrintAutomaticRequest(chan, data), parse_mode='HTML')
        else:
            BOT.send_message(message.from_user.id, '🔍 Нет автоматических заявок')
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, file)
    elif message.text == AUTO_BTNS[3]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def DeleteSingleRequest(message: Message) -> None:
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
    BOT.register_next_step_handler(message, SingleChoice)


def SingleChoice(message: Message) -> None:
    if message.text == SINGLE_BTNS[0]:
        SendActiveRequests(message)
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == SINGLE_BTNS[1]:
        SendFinishedRequests(message)
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
        BOT.register_next_step_handler(message, DeleteSingleRequest)
    elif message.text == SINGLE_BTNS[6]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте эмодзи:')
        BOT.register_next_step_handler(message, AcceptEmoji)
    elif message.text == SINGLE_BTNS[-1]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)


def ListAccountNumbers() -> str:
    res = ''
    for i, acc in enumerate(ACCOUNTS):
        res += f'{i + 1}) {acc.session.filename.split('/')[-1][:-8]}\n'
    return res


def ProcessAccountSms(message: Message, num: str, tzid: str, current_index: int, total: int) -> bool:
    Stamp(f'Checking for all sms', 'i')
    sms_dict = CheckAllSms(message)
    found = False
    if sms_dict and num in sms_dict:
        Stamp('Found incoming sms for recently bought number', 's')
        BOT.send_message(message.from_user.id, f'📲 Для номера {num} нашёл код: {sms_dict[num]}')
        found = True
    else:
        Stamp(f'No incoming sms for {num}', 'w')
        BOT.send_message(message.from_user.id, f'💤 Не вижу входящих сообщений для {num}')
    ShowButtons(message, BNT_NUM_OPERATION, '❔ Что делаем дальше?')
    BOT.register_next_step_handler(message, AbilityToCancel, num, tzid, current_index, total)
    return found


@ControlRecursion
def CancelNumber(message: Message, num: str, tzid: str) -> None:
    try:
        response = get(URL_CANCEL, params={'apikey': TOKEN_SIM, 'tzid': tzid, 'ban': 1, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while cancelling number {num}: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сервером для отмены номера, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        CancelNumber(message, num, tzid)
    else:
        if str(response.status_code)[0] == '2' and str(response.json()['response']) == '1':
            Stamp(f'Successful cancelling of number {num}', 's')
            BOT.send_message(message.from_user.id, f'❇️ Номер {num} отменён')
        else:
            Stamp(f'Failed to cancel number {num}: {response.text}', 'w')
            BOT.send_message(message.from_user.id, f'ℹ️ Пока что не удалось отменить номер, '
                                                    f'пробую ещё раз через {LONG_SLEEP * 2} секунд...')
            Sleep(LONG_SLEEP * 2)
            CancelNumber(message, num, tzid)


def AddAccounts(message: Message) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        req_quantity = int(message.text)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, f'❌ Пожалуйста, введите только число. Введите от 0 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    if req_quantity > MAX_ACCOUNTS_BUY or req_quantity <= 0:
        ShowButtons(message, CANCEL_BTN, f'❌ Введено некорректное число. Введите от 0 до {MAX_ACCOUNTS_BUY}:')
        BOT.register_next_step_handler(message, AddAccounts)
        return
    Stamp(f'Starting the process of {message.text} account addition', 'i')
    BOT.send_message(message.from_user.id, f'🔁 Начинаю процесс добавления {message.text} аккаунтов...')
    AddAccountRecursive(message, 0, req_quantity)


def AbilityToCancel(message: Message, num: str, tzid: str, current_index: int, total: int) -> None:
    if message.text == BNT_NUM_OPERATION[1]:
        Stamp(f'Cancelling number {num}', 'w')
        BOT.send_message(message.from_user.id, f'🆗 Отменяю номер {num} (занимает некоторое время)...')
        try:
            CancelNumber(message, num, tzid)
        except RecursionError:
            Stamp('Too many tries to cancel num, returning', 'w')
            BOT.send_message(message.from_user.id, '🛑 Слишком много попыток отмены номера, '
                                                   'перехожу к следующему...')
        AddAccountRecursive(message, current_index + 1, total)
        return
    if not ProcessAccountSms(message, num, tzid, current_index, total):
        return
    Stamp('Sending request to authorize on API', 'i')
    BOT.send_message(message.from_user.id, f'📮 Отправляю код на номер {num} для авторизации API')
    row = FigureOutFreeRow()
    proxy = GetProxy(row)
    if not row:
        Stamp(f'Exiting because of finding free row fail', 'w')
        BOT.send_message(message.from_user.id, f'⁉️ Не нашёл свободного прокси, '
                                  f'завершаю процесс покупки...')
        AddAccountRecursive(message, current_index + 1, total)
        return
    try:
        session, rand_hash = RequestAPICode(message, num, proxy)
    except RecursionError:
        Stamp(f'Exiting because of requesting code fail', 'w')
        BOT.send_message(message.from_user.id, '❗️ Превышено максимальное количество попыток,'
                                  'завершаю процесс покупки...')
        AddAccountRecursive(message, current_index + 1, total)
        return
    BOT.register_next_step_handler(message, HandleAPICode, session, num, rand_hash, proxy, row)


def AddAccountRecursive(message: Message, current_index: int, total: int) -> None:
    if current_index >= total:
        BOT.send_message(message.from_user.id, f'✅ Было обработано {total} аккаунтов')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    Stamp(f'Adding {current_index + 1} account', 'i')
    BOT.send_message(message.from_user.id, f'▫️ Добавляю {current_index + 1}-й аккаунт')
    try:
        num, tzid = BuyAccount(message)
    except RecursionError:
        Stamp(f'Exiting because of buying fail', 'w')
        BOT.send_message(message.from_user.id, '❗️ Превышено максимальное количество попыток,'
                                               'завершаю процесс покупки...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        return
    # num, tzid = '+18352303716', ''
    ShowButtons(message, BNT_NUM_OPERATION, '❕ Если аккаунт нужно отменить, воспользуйтесь кнопкой')
    BOT.register_next_step_handler(message, AbilityToCancel, num, tzid, current_index, total)


def ExtractCodeFromMessage(text: str) -> str | None:
    pattern = r'Вот он:\s*(\S+)'
    match = search(pattern, text, MULTILINE)
    if match:
        return match.group(1)
    return None


def HandleAPICode(message: Message, session: Session, num: str, rand_hash: str, proxy: dict, row: int) -> None:
    # TODO Unstable transition to this func: what if no msg from user?
    code = ExtractCodeFromMessage(message.text)
    if not code:
        Stamp('No valid API code from user found, exiting...', 'e')
        BOT.send_message(message.from_user.id, '❌ Не удалось извлечь код из сообщения, '
                                               'перехожу к следующему номеру...')
        return
    Stamp(f'API code received for number {num}: {code}', 's')
    BOT.send_message(message.from_user.id, f'✳️ Обнаружен код: {code}')
    try:
        session = LoginAPI(message, session, num, rand_hash, code, proxy)
    except RecursionError as e:
        Stamp(f'Failed to login into API: {e}', 'e')
        BOT.send_message(message.from_user.id, f'🚫 Не удалось авторизоваться в API с номера {num}, '
                                               f'перехожу к следующему номеру...')
        return
    Stamp(f'Getting HTML page for number {num}', 'i')
    BOT.send_message(message.from_user.id, f'⏩ Получаю данные об API_ID и API_HASH...')
    try:
        api_id, api_hash = GetAppData(message, session, proxy)
    except RecursionError:
        return
    Stamp(f'Got api_id: {api_id} and api_hash: {api_hash} for number {num}', 's')
    BOT.send_message(message.from_user.id, f'✅ Получил данные для номера {num}:\n'
                                           f'API_ID: {api_id}\n'
                                           f'API_HASH: {api_hash}\n'
                                           f'▶️ Заношу данные в таблицу...')
    UploadData([[num[1:], api_id, api_hash, '-']], EXTRA_SHEET_NAME, SHEET_ID, SERVICE, row)
    Stamp(f'Trying to authorize account {num}', 'i')
    BOT.send_message(message.from_user.id, '🔐 Авторизую аккаунт, ожидайте сообщения...')
    global NEW_ROW_TO_ADD, NEW_CHAT_ID
    NEW_ROW_TO_ADD = row
    NEW_CHAT_ID = message.from_user.id


def GetAppData(message: Message, session: Session, proxy: dict) -> (str, str):
    try:
        response = session.get(URL_API_GET_APP, headers=HEADERS, proxies=proxy)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during app data requesting: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с сайтом данных о приложении, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        api_id, api_hash = GetAppData(message, session, proxy)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Got HTML page', 's')
            BOT.send_message(message.from_user.id, f'♻️ Получил страницу сайта, ищу необходимые данные')
            api_id, api_hash = ParseHTML(response.text)
        else:
            Stamp('Did not got HTML page', 'e')
            BOT.send_message(message.from_user.id, f'📛 Не удалось получить страницу сайта с API_ID и API_HASH, '
                             f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            api_id, api_hash = GetAppData(message, session, proxy)
    return api_id, api_hash


def ParseHTML(page: str) -> (str, str):
    api_id_pattern = r'<label for="app_id" class="col-md-4 text-right control-label">App api_id:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*><strong>(\d+)</strong></span>'
    api_hash_pattern = r'<label for="app_hash" class="col-md-4 text-right control-label">App api_hash:</label>\s*<div class="col-md-7">\s*<span class="form-control input-xlarge uneditable-input"[^>]*>([a-f0-9]{32})</span>'
    api_id_match = search(api_id_pattern, page, IGNORECASE)
    api_hash_match = search(api_hash_pattern, page, IGNORECASE)
    api_id = api_id_match.group(1) if api_id_match else None
    api_hash = api_hash_match.group(1) if api_hash_match else None
    return api_id, api_hash


@ControlRecursion
def LoginAPI(message: Message, session: Session, num: str, rand_hash: str, code: str, proxy: dict) -> Session:
    data = {
        'phone': num,
        'random_hash': rand_hash,
        'password': code,
    }
    try:
        response = session.post(URL_API_LOGIN, headers=HEADERS, proxies=proxy, data=data)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server during API login: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с API для авторизации, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session = LoginAPI(message, session, num, rand_hash, code, proxy)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Logined into API for number {num}', 's')
            BOT.send_message(message.from_user.id, f'❇️ Зашёл в API для аккаунта {num}')
            print(response.json())
        else:
            Stamp(f'Failed to login into API: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'🛑 Не удалось зайти в API для номера {num}, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session = LoginAPI(message, session, num, rand_hash, code, proxy)
    return session


def FigureOutFreeRow() -> int | None:
    data = GetSector(LEFT_CORNER, RIGHT_CORNER, SERVICE, EXTRA_SHEET_NAME, SHEET_ID)
    for index, row in enumerate(data):
        if row[0] == '':
            return index + 2
    return


def GetProxy(row: int) -> dict:
    data = GetSector(f'E{row}', f'H{row}', SERVICE, EXTRA_SHEET_NAME, SHEET_ID)[0]
    proxies = {
        'http': f'socks5://{data[2]}:{data[3]}@{data[0]}:{data[1]}',
        'https': f'socks5://{data[2]}:{data[3]}@{data[0]}:{data[1]}'
    }
    return proxies


@ControlRecursion
def RequestAPICode(message: Message, num: str, proxy: dict) -> (Session, str):
    HEADERS['user-agent'] = choice(USER_AGENTS)
    session = Session()
    try:
        response = session.post(URL_API_GET_CODE, headers=HEADERS, data={'phone': num}, proxies=proxy)
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while requesting API code: {e}', 'e')
        BOT.send_message(message.from_user.id, f'‼️ Не удалось связаться с API для запроса кода, '
                                               f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP, 0.5)
        session, rand_hash = RequestAPICode(message, num, proxy)
    else:
        if str(response.status_code)[0] == '2':
            Stamp(f'Sent API code to {num}', 's')
            BOT.send_message(message.from_user.id, f'💬 Код для авторизации в API отправлен на {num}, '
                                                   f'проверьте сообщения от Telegram.\n⚠️ В ответ перешлите мне'
                                                   f'всё сообщение целиком.')
            rand_hash = response.json()['random_hash']
        else:
            Stamp(f'Failed to send API code to {num}: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'‼️ Не удалось запросить код для API, '
                                                   f'пробую ещё раз примерно через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP, 0.5)
            session, rand_hash = RequestAPICode(message, num, proxy)
    return session, rand_hash


@ControlRecursion
def BuyAccount(message: Message) -> tuple:
    try:
        response = get(URL_BUY, params={'apikey': TOKEN_SIM, 'service': 'telegram', 'country': 7, 'number': True, 'lang': 'ru'})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server while buying account: {e}', 'e')
        BOT.send_message(message.from_user.id, f'❌ Не удалось связаться с сервером покупки аккаунтов, '
                                               f'пробую ещё раз через {LONG_SLEEP} секунд...')
        Sleep(LONG_SLEEP)
        num, tzid = BuyAccount(message)
    else:
        if str(response.status_code)[0] == '2':
            if 'number' in response.json():
                num = response.json()['number']
                tzid = response.json()['tzid']
                Stamp(f'Bought account: {num}', 's')
                BOT.send_message(message.from_user.id, f'📱 Куплен номер {num} на 15 минут')
            else:
                Stamp(f'No "number" field in response <-> no available numbers in this region', 'e')
                BOT.send_message(message.from_user.id, '⛔️ Нет доступных номеров в этом регионе, '
                                                       'прекращаю процесс покупки...')
                raise RecursionError
        else:
            Stamp(f'Failed to buy account: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'❌ Не удалось купить аккаунт, '
                                                   f'пробую ещё раз через {LONG_SLEEP} секунд...')
            Sleep(LONG_SLEEP)
            num, tzid = BuyAccount(message)
    return num, tzid


def CheckAllSms(message: Message) -> dict | None:
    res = {}
    try:
        response = get(URL_SMS, params={'apikey': TOKEN_SIM})
    except ConnectionError as e:
        Stamp(f'Failed to connect to the server: {e}', 'e')
        BOT.send_message(message.from_user.id, f'❌ Не удалось связаться с сервером для получения кодов...')
    else:
        if str(response.status_code)[0] == '2':
            Stamp('See some data about sms', 's')
            for item in response.json():
                if 'msg' in item:
                    res[item['number']] = item['msg']
        else:
            Stamp(f'Failed to get list of sms: {response.text}', 'e')
            BOT.send_message(message.from_user.id, f'❌ Статус {response.status_code} при обновлении списка смс...')
    return res


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
        CODE = message.text
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    SERVICE = BuildService()
    # data = GetSector(LEFT_CORNER, RIGHT_CORNER, SERVICE, EXTRA_SHEET_NAME, SHEET_ID)
    Thread(target=BotPolling, daemon=True).start()
    run(Main())
