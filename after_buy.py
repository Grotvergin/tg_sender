from source import (BOT, NEW_CHAT_ID, IMG_PATH,
                    EXTRA_SHEET_NAME, SHORT_SLEEP, NEW_ROW_TO_ADD)
from secret import SHEET_ID
from common import Stamp, GetSector, BuildService
from random import choice
from requests import get
from PIL import Image
from io import BytesIO
from os import remove, getcwd
from os.path import join
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from socks import SOCKS5
from telethon.errors import (PhoneCodeInvalidError,
                             PhoneCodeExpiredError,
                             SessionPasswordNeededError,
                             PhoneNumberInvalidError)
from common import SkippedCodeInsertion, ParseAccountRow
from traceback import format_exc
from auth import AuthCallback
from asyncio import sleep as async_sleep
from random import randint


async def CheckNewAuth() -> None:
    global NEW_ROW_TO_ADD
    while True:
        if NEW_ROW_TO_ADD:
            BOT.send_message(NEW_CHAT_ID, '🔐 Авторизую аккаунт, ожидайте сообщения...')
            Stamp(f'New row to add is set, authorizing account on row {NEW_ROW_TO_ADD}', 'i')
            await AuthNewAccount(NEW_ROW_TO_ADD)
            NEW_ROW_TO_ADD = None
        await async_sleep(SHORT_SLEEP)


def GenerateRandomRussianName() -> (str, str):
    first_names = ['Алексей', 'Андрей', 'Борис', 'Владимир', 'Георгий', 'Дмитрий', 'Евгений', 'Игорь', 'Константин', 'Максим']
    last_names = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Петров']
    return choice(first_names), choice(last_names)


def GenerateRandomDescription() -> str:
    descriptions = [
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
        'Интересуюсь искусством и культурой.',
        'Занимаюсь фотографией и видеосъемкой.'
    ]
    return choice(descriptions)


def GetRandomProfilePicture() -> str | None:
    try:
        response = get('https://picsum.photos/400')
    except ConnectionError as e:
        BOT.send_message(NEW_CHAT_ID, f'❌ Ошибка при получении случайного изображения')
        Stamp(f'Failed to get random image: {e}', 'e')
        return None
    else:
        img = Image.open(BytesIO(response.content))
        img.save(IMG_PATH)
        return IMG_PATH


async def SetProfilePicture(client: TelegramClient) -> None:
    Stamp('Setting profile picture', 'i')
    BOT.send_message(NEW_CHAT_ID, '🖼 Изменяю фотографию профиля...')
    file = await client.upload_file(IMG_PATH)
    await client(UploadProfilePhotoRequest(file))
    remove(IMG_PATH)


async def SetProfileInfo(client: TelegramClient) -> None:
    Stamp('Setting profile info', 'i')
    BOT.send_message(NEW_CHAT_ID, '📝 Изменяю информацию профиля...')
    first_name, last_name = GenerateRandomRussianName()
    about = GenerateRandomDescription()
    await client(UpdateProfileRequest(first_name=first_name,
                                      last_name=last_name,
                                      about=about))


async def AddContacts(client: TelegramClient, num: int) -> None:
    Stamp(f'Adding {num} contacts', 'i')
    BOT.send_message(NEW_CHAT_ID, f'📞 Добавляю {num} контактов...')
    contacts = []
    for _ in range(num):
        first_name, last_name = GenerateRandomRussianName()
        phone = f'+{randint(1, 99)}{randint(1000000000, 9999999999)}'
        contact = InputPhoneContact(client_id=randint(0, 999999),
                                    phone=phone,
                                    first_name=first_name,
                                    last_name=last_name)
        contacts.append(contact)
    await client(ImportContactsRequest(contacts))


async def AuthNewAccount(row: int) -> None:
    data = GetSector(f'A{row}', f'H{row}', BuildService(), EXTRA_SHEET_NAME, SHEET_ID)[0]
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
        await SetProfileInfo(client)
        await SetProfilePicture(client)
        await AddContacts(client, 10)
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
