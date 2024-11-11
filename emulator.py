from common import Stamp, Sleep, ErrorAfterNumberInsertion, PasswordRequired
from source import HOME_KEYCODE, BOT, MIN_LEN_EMAIL, SHORT_SLEEP, MAX_RECURSION
from secret import UDID, APPIUM, PASSWORD
from generator import GenerateRandomRussianName, GenerateRandomWord
# ---
from re import search, MULTILINE
from time import sleep
# ---
from selenium.common.exceptions import NoSuchElementException
from requests import get, post
from appium.webdriver import Remote
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options


def PrepareDriver() -> Remote:
    options = UiAutomator2Options()
    options.set_capability("disableWindowAnimation", True)
    options.set_capability("platformName", "Android")
    options.set_capability("deviceName", "Mi")
    options.set_capability("noReset", True)
    options.set_capability("udid", UDID)
    options.set_capability("newCommandTimeout", 3600)
    driver = Remote(APPIUM, options=options)
    return driver


def BackToHomeScreen(driver: Remote):
    try:
        driver.press_keycode(HOME_KEYCODE)
        Stamp('Got back to home screen', 's')
    except NoSuchElementException:
        Stamp(f'Failed to get back to home screen', 'e')


def CloseTelegramApp(driver: Remote):
    try:
        driver.terminate_app('org.telegram.messenger.web')
        Stamp('Telegram app closed successfully', 's')
    except NoSuchElementException:
        Stamp(f'Failed to close Telegram app', 'e')


def PressButton(driver: Remote, path: str, name: str, interval: int, by: str = AppiumBy.XPATH):
    try:
        btn = driver.find_element(by=by, value=path)
        btn.click()
        Stamp(f'Button {name} pressed successfully', 's')
    except NoSuchElementException:
        Stamp(f'Failed to find or press button {name}', 'e')
    Sleep(interval)


def InsertField(driver: Remote, path: str, name: str, text: str, interval: int):
    try:
        field = driver.find_element(by=AppiumBy.XPATH, value=path)
        field.clear()
        field.send_keys(text)
        Stamp(f'Field {name} filled successfully', 's')
    except NoSuchElementException:
        Stamp(f'Failed to find or fill field {name}', 'e')
    Sleep(interval)


def DistributedInsertion(driver: Remote, path: str, name: str, text: str, big_interval: int, small_interval: int):
    try:
        for i in range(1, len(text) + 1):
            field = driver.find_element(by=AppiumBy.XPATH, value=path.format(i))
            field.clear()
            field.send_keys(text[i - 1])
            sleep(small_interval)
        Stamp(f'Field {name} filled successfully', 's')
    except NoSuchElementException:
        Stamp(f'Failed to find or fill field {name}', 'e')
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


def GetEmailCode(token: str, max_attempts: int = MAX_RECURSION) -> str | None:
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
        Sleep(SHORT_SLEEP * 5)
    Stamp('Failed to get email code', 'w')
    return


def SetPassword(driver: Remote, user_id: int) -> None:
    Stamp('Setting password ', 'i')
    BOT.send_message(user_id, f'🔒 Установка пароля')
    PressButton(driver, '//android.widget.ImageView[@content-desc="Open navigation menu"]', 'Menu', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Settings"])[2]', 'Settings', 3)
    PressButton(driver, '//android.widget.TextView[@text="Privacy and Security"]', 'Privacy & Security', 3)
    PressButton(driver, '//android.widget.TextView[@text="Two-Step Verification"]', 'Two-Step Verification', 3)
    PressButton(driver, '//android.widget.TextView[@text="Set Password"]', 'Set Password', 3)
    InsertField(driver, '//android.widget.EditText[@content-desc="Enter password"]', 'Password', PASSWORD, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    InsertField(driver, '//android.widget.EditText[@content-desc="Re-enter password"]', 'Password repeat', PASSWORD, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    PressButton(driver, '//android.widget.TextView[@text="Skip"]', 'Skip', 3)
    while True:
        email, token = GetTemporaryEmail(MIN_LEN_EMAIL, PASSWORD)
        InsertField(driver, '//android.widget.EditText[@content-desc="Email"]', 'Email', email, 5)
        if IsElementPresent(driver, '//android.widget.TextView[@text="An error occurred.EMAIL_NOT_ALLOWED"]'):
            PressButton(driver, '//android.widget.TextView[@text="OK"]', 'OK after email is not allowed', 3)
            PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after email is not allowed', 3)
            continue
        break
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    code = GetEmailCode(token)
    DistributedInsertion(driver, '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]', 'Email code', code, 3, 1)
    PressButton(driver, '//android.widget.TextView[@text="Return to Settings"]', 'Done', 3)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Go back"]', 'Back', 2)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Go back"]', 'Another back', 2)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Go back"]', 'Final back', 2)
    Stamp('Password set successfully', 's')
    BOT.send_message(user_id, f'❇️ Пароль для аккаунта установлен')


def AskForCode(driver: Remote, num: str, user_id: int, len_country_code: int) -> None:
    Stamp(f'Asking for code', 'i')
    BOT.send_message(user_id, f'📲 Запрос кода для входа в Telegram')
    CloseTelegramApp(driver)
    BackToHomeScreen(driver)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Telegram"]', 'Telegram', 3)
    PressButton(driver, '//android.widget.TextView[@text="Start Messaging"]', 'Start Messaging', 3)
    country_code = num[1:1 + len_country_code]
    phone_number = num[1 + len_country_code:]
    InsertField(driver, '//android.widget.EditText[@content-desc="Country code"]', 'Country code', country_code, 2)
    InsertField(driver, '//android.widget.EditText[@content-desc="Phone number"]', 'Phone number', phone_number, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View', '->', 3)
    PressButton(driver, '//android.widget.TextView[@text="Yes"]', 'Yes', 10)
    if IsElementPresent(driver, '//android.widget.TextView[@text="This phone number is banned."]'):
        raise ErrorAfterNumberInsertion
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Check your Telegram messages"]'):
        PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after check your messages', 3)
        PressButton(driver, '//android.widget.TextView[@text="Edit"]', 'Edit after check your messages', 3)
        raise ErrorAfterNumberInsertion
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Choose a login email"]'):
        email, token = GetTemporaryEmail(MIN_LEN_EMAIL, PASSWORD)
        InsertField(driver, '//android.widget.EditText', 'Email', email, 2)
        PressButton(driver, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View', 'Done', 4)
        code = GetEmailCode(token)
        DistributedInsertion(driver,
                             '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]',
                             'Verification Code', code, 4, 1)
        if IsElementPresent(driver, '//android.widget.TextView[@text="An error occurred.\nEMAIL_NOT_ALLOWED"]'):
            PressButton(driver, '//android.widget.TextView[@text="OK"]', 'OK after email is not allowed', 3)
            PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after email is not allowed', 3)
            PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Another back after email is not allowed', 3)
            raise ErrorAfterNumberInsertion
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Check Your Email"]'):
        PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after email is not allowed', 3)
        raise ErrorAfterNumberInsertion
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Too many attempts, please try again later."]'):
        PressButton(driver, '//android.widget.TextView[@text="OK"]', 'OK', 1)
        Stamp('Clearing cache', 'i')
        driver.execute_script("mobile: shell", {
            'command': 'pm clear',
            'args': 'org.telegram.messenger',
            'includeStderr': True,
            'timeout': 5000
        })
        raise ErrorAfterNumberInsertion
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Your password"]'):
        PressButton(driver, '//android.widget.ImageView[@content-desc="Back"]', 'Back after password required', 3)
        raise PasswordRequired
    elif IsElementPresent(driver, '//android.widget.TextView[@text="Invalid phone number. Please check the number and try again."]'):
        PressButton(driver, '//android.widget.TextView[@text="OK"]', 'OK after invalid phone number', 3)
        raise ErrorAfterNumberInsertion
    Stamp('Code requested successfully', 's')
    BOT.send_message(user_id, f'🔑 Код для входа в Telegram запрошен')


def InsertCode(driver: Remote, user_id: int, code: str) -> None:
    Stamp('Inserting code', 'i')
    BOT.send_message(user_id, f'🗝 Ввод кода {code}')
    DistributedInsertion(driver,
                         '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]',
                         'Code', code, 3, 1)
    Stamp('Code inserted successfully', 's')
    BOT.send_message(user_id, f'✅ Код {code} введен')
    if IsElementPresent(driver, '//android.widget.TextView[@text="Profile info"]'):
        first_name, last_name = GenerateRandomRussianName()
        InsertField(driver,
                    '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.FrameLayout[1]/android.widget.EditText',
                    'First Name', first_name, 4)
        InsertField(driver,
                    '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.FrameLayout[2]/android.widget.EditText',
                    'Last Name', last_name, 3)
        PressButton(driver, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View', 'Done', 1)
    Sleep(10)
    PressButton(driver, '//android.widget.TextView[@text="Not now"]', 'Not now in allowing contacts', 3)


def ExtractCodeFromMessage(driver: Remote) -> str | None:
    element = driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Код")')
    pattern = r'Вот он:\s*(\S+)'
    found = search(pattern, element.text, MULTILINE)
    if found:
        return found.group(1)
    return


def ExitFromAccount(driver: Remote):
    PressButton(driver, '//android.widget.ImageView[@content-desc="Open navigation menu"]', '|||', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Settings"])[2]', 'Settings', 3)
    PressButton(driver, '//android.widget.ImageButton[@content-desc="More options"]/android.widget.ImageView', '...', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])', 'Logout', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])[2]', 'One more logout', 3)
    PressButton(driver, '(//android.widget.TextView[@text="Log Out"])[2]', 'Final logout', 3)
