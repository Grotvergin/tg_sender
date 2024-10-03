import time
from appium.webdriver import Remote
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from common import Stamp, Sleep, AccountIsBanned, WeSentCodeToDevice
from source import (HOME_KEYCODE, PLATFORM_NAME, DEVICE_NAME, ATTEMPTS_EMAIL,
                    URL_DEVICE, BOT, MIN_LEN_EMAIL, SHORT_SLEEP, UDID)
from secret import BOT_NAME, XPATH_TO_BOT, PASSWORD
from selenium.common.exceptions import NoSuchElementException
from requests import get, post
from api import GenerateRandomWord
from re import search


def PrepareDriver() -> Remote:
    options = UiAutomator2Options()
    options.set_capability("disableWindowAnimation", True)
    options.platform_name = PLATFORM_NAME
    options.device_name = DEVICE_NAME
    options.no_reset = True
    options.udid = UDID
    driver = Remote(URL_DEVICE, options=options)
    return driver


def BackToHomeScreen(driver: Remote):
    try:
        driver.press_keycode(HOME_KEYCODE)
        Stamp('Got back to home screen', 's')
    except Exception as e:
        Stamp(f'Failed to get back to home screen: {e}', 'e')


def CloseTelegramApp(driver: Remote):
    try:
        driver.terminate_app('org.telegram.messenger.web')
        Stamp('Telegram app closed successfully', 's')
    except Exception as e:
        Stamp(f'Failed to close Telegram app: {e}', 'e')


def PressButton(driver: Remote, path: str, name: str, interval: int, by: str = AppiumBy.XPATH):
    try:
        btn = driver.find_element(by=by, value=path)
        btn.click()
        Stamp(f'Button {name} pressed successfully', 's')
    except Exception as e:
        Stamp(f'Failed to find or press button {name}: {e}', 'e')
    Sleep(interval)


def InsertField(driver: Remote, path: str, name: str, text: str, interval: int):
    try:
        field = driver.find_element(by=AppiumBy.XPATH, value=path)
        field.clear()
        field.send_keys(text)
        Stamp(f'Field {name} filled successfully', 's')
    except Exception as e:
        Stamp(f'Failed to find or fill field {name}: {e}', 'e')
    Sleep(interval)


def DistributedInsertion(driver: Remote, path: str, name: str, text: str, big_interval: int, small_interval: int):
    try:
        for i in range(1, len(text) + 1):
            field = driver.find_element(by=AppiumBy.XPATH, value=path.format(i))
            field.clear()
            field.send_keys(text[i - 1])
            time.sleep(small_interval)
        Stamp(f'Field {name} filled successfully', 's')
    except Exception as e:
        Stamp(f'Failed to find or fill field {name}: {e}', 'e')
    Sleep(big_interval)


def IsElementPresent(driver: Remote, path: str, by: str = AppiumBy.XPATH) -> bool:
    try:
        driver.find_element(by=by, value=path)
        return True
    except NoSuchElementException:
        return False


def GetTemporaryEmail(min_len: int, password: str) -> (str, str):
    Stamp('Getting temporary email', 'i')
    response = get('https://api.mail.tm/domains')
    domain = response.json()['hydra:member'][0]['domain']
    email_username = GenerateRandomWord(min_len)
    email = f'{email_username}@{domain}'
    data = {
        "address": email,
        "password": password
    }
    post('https://api.mail.tm/accounts', json=data)
    token_response = post('https://api.mail.tm/token', json=data)
    token = token_response.json()['token']
    Stamp(f'Temporary email {email} received successfully', 's')
    return email, token


def GetEmailCode(token: str, max_attempts: int = ATTEMPTS_EMAIL) -> str | None:
    Stamp('Getting email code', 'i')
    for _ in range(max_attempts):
        response = get('https://api.mail.tm/messages', headers={'Authorization': f'Bearer {token}'})
        messages = response.json()['hydra:member']
        if messages:
            Stamp('Email message received', 's')
            code_message = messages[0]['subject']
            match = search(r'\b\d{6}\b', code_message)
            if match:
                Stamp('Email code received successfully', 's')
                return match.group(0)
            else:
                Stamp('Email code not found in the message', 'w')
        Sleep(SHORT_SLEEP*5)
    Stamp('Failed to get email code', 'w')
    return


def SetPassword(user_id: int, password: str) -> None:
    Stamp('Setting password ', 'i')
    BOT.send_message(user_id, f'🔒 Установка пароля для аккаунта')
    driver = PrepareDriver()
    CloseTelegramApp(driver)
    BackToHomeScreen(driver)
    PressButton(driver, '//android.widget.TextView[@content-desc="Telegram"]', 'Telegram', 3)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Open navigation menu"]', 'Menu', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Settings"])[2]', 'Settings', 3)
    PressButton(driver, '//android.widget.TextView[@text="Privacy and Security"]', 'Privacy & Security', 3)
    PressButton(driver, '//android.widget.TextView[@text="Two-Step Verification"]', 'Two-Step Verification', 3)
    PressButton(driver, '//android.widget.TextView[@text="Set Password"]', 'Set Password', 3)
    InsertField(driver, '//android.widget.EditText[@content-desc="Enter password"]', 'Password', password, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    InsertField(driver, '//android.widget.EditText[@content-desc="Re-enter password"]', 'Password repeat', password, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    PressButton(driver, '//android.widget.TextView[@text="Skip"]', 'Skip', 3)
    email, token = GetTemporaryEmail(MIN_LEN_EMAIL, password)
    InsertField(driver, '//android.widget.EditText[@content-desc="Email"]', 'Email', email, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    code = GetEmailCode(token)
    DistributedInsertion(driver, '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]', 'Email code', code, 3, 1)
    PressButton(driver, '//android.widget.TextView[@text="Return to Settings"]', 'Done', 3)
    driver.close()
    driver.quit()
    Stamp('Password set successfully', 's')
    BOT.send_message(user_id, f'❇️ Пароль для аккаунта установлен')


def AskForCode(user_id: int, num: str, len_country_code: int) -> None:
    Stamp('Asking for code', 'i')
    BOT.send_message(user_id, f'💎 Запрос кода для номера {num}')
    driver = PrepareDriver()
    CloseTelegramApp(driver)
    BackToHomeScreen(driver)
    PressButton(driver, '//android.widget.TextView[@content-desc="Telegram"]', 'Telegram', 3)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Open navigation menu"]', '|||', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Settings"])[2]', 'Settings', 3)
    PressButton(driver, '//android.widget.ImageButton[@content-desc="More options"]/android.widget.ImageView', '...', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])', 'Logout', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])[2]', 'One more logout', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])[2]', 'Final logout', 3)
    PressButton(driver, '//android.widget.TextView[@text="Start Messaging"]', 'Start Messaging', 3)
    country_code = num[1:1 + len_country_code]
    phone_number = num[1 + len_country_code:]
    InsertField(driver, '//android.widget.EditText[@content-desc="Country code"]', 'Country code', country_code, 2)
    InsertField(driver, '//android.widget.EditText[@content-desc="Phone number"]', 'Phone number', phone_number, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View', '->', 3)
    PressButton(driver, '//android.widget.TextView[@text="Yes"]', 'Yes', 10)
    if IsElementPresent(driver, '//android.widget.TextView[@text="This phone number is banned."]'):
        PressButton(driver, '//android.widget.TextView[@text="OK"]', 'OK', 3)
        Stamp(f'Account {num} is banned, exiting', 'w')
        BOT.send_message(user_id, f'🚫 Аккаунт {num} заблокирован, выхожу из процедуры')
        raise AccountIsBanned
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Check your Telegram messages"]'):
        PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back', 3)
        PressButton(driver, '//android.widget.TextView[@text="Edit"]', 'Edit', 3)
        Stamp(f'Code was sent to Telegram, exiting', 'w')
        BOT.send_message(user_id, f'🚫 Код был отправлен на другое устройство, выхожу из процедуры')
        raise WeSentCodeToDevice
    driver.close()
    driver.quit()
    Stamp('Code requested successfully', 's')
    BOT.send_message(user_id, f'🔑 Код для номера {num} запрошен')


def InsertCode(user_id: int, code: str) -> None:
    Stamp('Inserting code', 'i')
    BOT.send_message(user_id, f'🗝 Ввод кода в эмуляторе {code}')
    driver = PrepareDriver()
    DistributedInsertion(driver,
                         '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]',
                         'Code', code, 3, 1)
    driver.close()
    driver.quit()
    Stamp('Code inserted successfully', 's')
    BOT.send_message(user_id, f'✅ Код {code} введен')


def ForwardMessage(user_id: int) -> None:
    Stamp('Forwarding message', 'i')
    BOT.send_message(user_id, '📨 Пересылаю сообщение с кодом для API')
    driver = PrepareDriver()
    PressButton(driver, 'new UiSelector().className("android.view.ViewGroup").index(0)', 'Chat', 3, by=AppiumBy.ANDROID_UIAUTOMATOR)
    PressButton(driver, 'new UiSelector().textContains("Код")', 'Message', 3, by=AppiumBy.ANDROID_UIAUTOMATOR)
    PressButton(driver, '//android.widget.TextView[@text="Forward"]', 'Forward', 3)
    PressButton(driver, '//android.widget.ImageButton[@content-desc="Search"]/android.widget.ImageView', 'Search', 3)
    InsertField(driver, '//android.widget.EditText[@text="Search"]', 'Search', BOT_NAME, 2)
    PressButton(driver, XPATH_TO_BOT, 'Our Bot', 3)
    PressButton(driver, '//android.widget.TextView[@text="START"]', 'Start', 3)
    PressButton(driver, '//android.view.View[@content-desc="Send"]', 'Send', 3)
    driver.close()
    driver.quit()
    Stamp('Message forwarded successfully', 's')
    BOT.send_message(user_id, '📩 Сообщение переслано в бота')
