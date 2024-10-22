import source
from source import BOT, IMG_PATH, LEFT_CORNER, RIGHT_CORNER
from common import Stamp, UploadData, GetSector, BuildService
from emulator import SetPassword, PrepareDriver
from secret import PASSWORD, PROXY_KEY, SHEET_ID, SHEET_NAME
from generator import GenerateRandomRussianName
# ---
from io import BytesIO
from os import remove, getcwd
from os.path import split, join
from random import randint, choice
from asyncio import sleep as async_sleep
# ---
from requests import get, RequestException
from PIL import Image
from socks import SOCKS5
from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, SetPrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import (InputPrivacyValueDisallowAll,
                               InputPrivacyKeyPhoneNumber,
                               InputPrivacyKeyPhoneCall,
                               InputPrivacyKeyChatInvite,
                               InputPrivacyKeyStatusTimestamp,
                               InputPhoneContact)


def buyProxy(api_key):
    url = f"https://proxy6.net/api/{api_key}/buy"
    params = {
        'count': 1,
        'period': 30,
        'country': 'ru',
        'version': 3,
        'type': 'socks'
    }
    try:
        response = get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'yes':
            proxy_data = list(data['list'].values())[0]
            proxy = (
                SOCKS5,
                proxy_data['host'],
                proxy_data['port'],
                True,
                proxy_data['user'],
                proxy_data['pass']
            )
            return proxy
        else:
            raise Exception(f"Error: {data}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        return
    except Exception as e:
        Stamp(f'An error occurred: {e}', 'e')
        return


async def CheckProfileChange() -> None:
    while True:
        if source.ACC_TO_CHANGE:
            SetPassword(PrepareDriver(), source.ADMIN_CHAT_ID, PASSWORD)
            proxy = buyProxy(PROXY_KEY)
            num, api_id, api_hash = source.ACC_TO_CHANGE.split('|')
            session = join(getcwd(), 'sessions', f'{num}')
            client = TelegramClient(session, api_id, api_hash, proxy=proxy)
            await client.start(phone=num, password=PASSWORD, code_callback=lambda: emuAuthCallback())
            source.ACCOUNTS.append(client)
            Stamp(f'Account {num} authorized', 's')
            BOT.send_message(source.ADMIN_CHAT_ID, f'✅ Аккаунт {num} авторизован')
            await SetProfileInfo(source.ACC_TO_CHANGE, source.ADMIN_CHAT_ID)
            await SetProfilePicture(source.ACC_TO_CHANGE, source.ADMIN_CHAT_ID)
            await AddContacts(source.ACC_TO_CHANGE, 50, source.ADMIN_CHAT_ID)
            await UpdatePrivacySettings(source.ACC_TO_CHANGE, source.ADMIN_CHAT_ID)
            srv = BuildService()
            row = len(GetSector(LEFT_CORNER, RIGHT_CORNER, srv, SHEET_NAME, SHEET_ID)) + 2
            UploadData([[num, api_id, api_hash, '-', proxy[1], proxy[2], proxy[4], proxy[5]]], SHEET_NAME, SHEET_ID, srv, row)
            Stamp(f'Data for number {num} added to the table', 's')
            BOT.send_message(source.ADMIN_CHAT_ID, f'📊 Данные для номера {num} занесены в таблицу')
            source.ACC_TO_CHANGE = None
        await async_sleep(source.SHORT_SLEEP)


def emuAuthCallback() -> int:
    pass


def FindAccountByNumber(num: int) -> TelegramClient | None:
    for acc in source.ACCOUNTS:
        if int(split(acc.session.filename)[-1][:-8]) == num:
            return acc
    return None


def GenerateRandomDescription() -> str:
    descriptions = [
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
        'Интересуюсь искусством и культурой.',
        'Занимаюсь фотографией и видеосъемкой.'
    ]
    return choice(descriptions)


def GetRandomProfilePicture(user_id: int) -> None:
    Stamp('Getting random profile picture', 'i')
    try:
        response = get('https://picsum.photos/400')
    except ConnectionError as e:
        BOT.send_message(user_id, f'❌ Ошибка при получении случайного изображения')
        Stamp(f'Failed to get random image: {e}', 'e')
    else:
        Stamp('Saving random profile picture', 'i')
        img = Image.open(BytesIO(response.content))
        img.save(IMG_PATH)


async def SetProfilePicture(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile picture', 'i')
    BOT.send_message(user_id, '🖼 Изменяю фотографию профиля...')
    GetRandomProfilePicture(user_id)
    file = await client.upload_file(IMG_PATH)
    await client(UploadProfilePhotoRequest(file=file))
    remove(IMG_PATH)


async def SetProfileInfo(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile info', 'i')
    BOT.send_message(user_id, '📝 Изменяю ФИО и описание...')
    first_name, last_name = GenerateRandomRussianName()
    await client(UpdateProfileRequest(about=GenerateRandomDescription(),
                                      first_name=first_name,
                                      last_name=last_name))


async def AddContacts(client: TelegramClient, num: int, user_id: int) -> None:
    Stamp(f'Adding {num} contacts', 'i')
    BOT.send_message(user_id, f'📞 Добавляю контакты...')
    contacts = []
    for _ in range(num):
        first_name, last_name = GenerateRandomRussianName()
        phone = f'+7{randint(900, 999)}{randint(1000000, 9999999)}'
        contact = InputPhoneContact(client_id=randint(100000, 999999),
                                    phone=phone,
                                    first_name=first_name,
                                    last_name=last_name)
        contacts.append(contact)
    await client(ImportContactsRequest(contacts))


async def UpdatePrivacySettings(client: TelegramClient, user_id: int) -> None:
    Stamp('Updating privacy settings', 'i')
    BOT.send_message(user_id, '🔒 Обновляю настройки приватности...')
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyPhoneNumber(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyPhoneCall(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyStatusTimestamp(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyChatInvite(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
