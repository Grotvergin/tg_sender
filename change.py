import source
from source import BOT, IMG_PATH
from common import Stamp
from generator import GenerateRandomRussianName, GenerateRandomDescription, GetRandomProfilePicture
# ---
from os import remove
from os.path import split
from random import randint
# ---
from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, SetPrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import (InputPrivacyValueDisallowAll, InputPrivacyKeyPhoneNumber, InputPrivacyKeyPhoneCall,
                               InputPrivacyKeyChatInvite, InputPrivacyKeyStatusTimestamp, InputPhoneContact)


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
