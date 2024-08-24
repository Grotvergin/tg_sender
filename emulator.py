import time
from appium.webdriver import Remote
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from common import Stamp, Sleep
from source import (HOME_KEYCODE, PLATFORM_NAME, DEVICE_NAME,
                    URL_DEVICE, SLEEP_BEFORE_CODE, BOT)
from secret import BOT_NAME, XPATH_TO_BOT


def PrepareDriver() -> Remote:
    options = UiAutomator2Options()
    options.platform_name = PLATFORM_NAME
    options.device_name = DEVICE_NAME
    options.no_reset = True
    driver = Remote(URL_DEVICE, options=options)
    return driver


def BackToHomeScreen(driver: Remote):
    try:
        driver.press_keycode(HOME_KEYCODE)
        Stamp('Got back to home screen', 's')
    except Exception as e:
        Stamp(f'Failed to get back to home screen: {e}', 'e')


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


def SetPassword(user_id: int, password: str, email: str) -> None:
    Stamp('Setting password ', 'i')
    BOT.send_message(user_id, f'🔒 Установка пароля для аккаунта {email}')
    driver = PrepareDriver()
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
    InsertField(driver, '//android.widget.EditText[@content-desc="Email"]', 'Email', email, 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Next"]', 'Next', 3)
    code = input('Введите код из почты:')
    DistributedInsertion(driver, '//android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[{}]', 'Email code', code, 3, 1)
    PressButton(driver, '//android.widget.TextView[@text="Return to Settings"]', 'Done', 3)
    driver.close()
    driver.quit()
    Stamp('Password set successfully', 's')
    BOT.send_message(user_id, f'❇️ Пароль для аккаунта {email} установлен')


def AskForCode(user_id: int, num: str) -> None:
    Stamp('Asking for code', 'i')
    BOT.send_message(user_id, f'💎 Запрос кода для номера {num}')
    driver = PrepareDriver()
    BackToHomeScreen(driver)
    PressButton(driver, '//android.widget.TextView[@content-desc="Telegram"]', 'Telegram', 3)
    PressButton(driver, '//android.widget.TextView[@text="Start Messaging"]', 'Start Messaging', 3)
    InsertField(driver, '//android.widget.EditText[@content-desc="Country code"]', 'Phone number', num[1], 2)
    InsertField(driver, '//android.widget.EditText[@content-desc="Phone number"]', 'Phone number', num[2:], 2)
    PressButton(driver, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View', 'Arrow', 3)
    PressButton(driver, '//android.widget.TextView[@text="Yes"]', 'Yes', 3)
    element = driver.find_element(by=AppiumBy.XPATH,
                                    value=f'//android.widget.ScrollView/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText[1]')
    if not element:
        Stamp(f'First Code field was not found on the page, waiting for {SLEEP_BEFORE_CODE} seconds', 'w')
        BOT.send_message(user_id, f'⏳ Ожидаю {SLEEP_BEFORE_CODE} секунд до появления возможности запросить код для номера {num}')
        Sleep(SLEEP_BEFORE_CODE)
        PressButton(driver, '//android.widget.TextView[@text="Get the code via SMS"]', 'Get the code via SMS', 3)
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
