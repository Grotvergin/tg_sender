import source
from source import BOT, IMG_PATH, URL_BUY_PROXY, URL_RECEIVE_PROXY
from common import Stamp
from generator import GenerateRandomRussianName, GenerateRandomDescription, GetRandomProfilePicture
# ---
from os import remove
from os.path import split
from random import randint
# ---
from requests import RequestException, post
from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, SetPrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import (InputPrivacyValueDisallowAll, InputPrivacyKeyPhoneNumber, InputPrivacyKeyPhoneCall,
                               InputPrivacyKeyChatInvite, InputPrivacyKeyStatusTimestamp, InputPhoneContact)


def buyProxy(user_id: int):
    Stamp('Buying proxy', 'i')
    BOT.send_message(user_id, '🔒 Покупаю прокси...')
    payload = {'PurchaseBilling':
        {
            "count": 1,
            "duration": 30,
            'type': 102,
            'country': 'ru'
        }
    }
    try:
        response = post(URL_BUY_PROXY, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            Stamp('Proxy bought', 's')
            BOT.send_message(user_id, '✅ Прокси куплен')
        else:
            error_code = data.get('code', 'UNKNOWN_ERROR')
            Stamp(f'Error while buying proxy: {error_code}', 'e')
            BOT.send_message(user_id, f'❌ Ошибка при покупке прокси: {error_code}')
            raise Exception(f"Error code: {error_code}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        BOT.send_message(user_id, '❌ Ошибка при покупке прокси. Проверьте соединение.')


def receiveProxyInfo(user_id: int) -> tuple:
    Stamp('Receiving proxy', 'i')
    BOT.send_message(user_id, '🔒 Получаю данные о прокси...')
    payload = {
        "type": "ipv4-shared",
        "proxy_type": "server",
        "page": 1,
        "page_size": 1,
        "sort": 0
    }
    try:
        response = post(URL_RECEIVE_PROXY, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            cur = data['list']['data'][0]
            socks_proxy = (2, cur['ip'], int(cur['socks_port']), True, cur['login'], cur['password'])
            http_proxy = (1, cur['ip'], int(cur['http_port']), True, cur['login'], cur['password'])
            Stamp(f'Proxy received: {http_proxy}', 's')
            BOT.send_message(user_id, f'🟢 Прокси получен: {http_proxy}')
            return socks_proxy, http_proxy
        else:
            error_code = data.get('message', 'UNKNOWN_ERROR')
            Stamp(f'Error while receiving proxy: {error_code}', 'e')
            BOT.send_message(user_id, f'❌ Ошибка при покупке прокси: {error_code}')
            raise Exception(f"Error code: {error_code}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        BOT.send_message(user_id, '❌ Ошибка при получении прокси. Проверьте соединение.')


def FindAccountByNumber(num: int) -> TelegramClient | None:
    for acc in source.ACCOUNTS:
        if int(split(acc.session.filename)[-1][:-8]) == num:
            return acc
    return None


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
