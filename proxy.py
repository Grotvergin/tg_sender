from requests import get, RequestException
from common import Stamp
from source import URL_GET_PROXY, BOT, URL_SET_COMMENT_PROXY


def getProxyByComment(user_id, comment):
    Stamp('Trying to get proxy', 'i')
    try:
        response = get(URL_GET_PROXY)
        data = response.json()

        if data['status'] == 'yes':
            Stamp('Got a list of proxy, searching for a free one', 's')
            for proxy_id, proxy_data in data['list'].items():
                if proxy_data.get('descr') == comment:
                    Stamp('Found a free proxy', 's')
                    BOT.send_message(user_id, f"🟩 Нашёл свободный прокси {proxy_data['host']}:{proxy_data['port']}")
                    socks_proxy = (2, proxy_data['host'], int(proxy_data['port']), True, proxy_data['user'], proxy_data['pass'])
                    return socks_proxy, proxy_id
            Stamp('No free proxies', 'e')
            BOT.send_message(user_id, '🟥 Нет свободных прокси')
            return
        else:
            Stamp(f'Error when getting list of proxies: {data.get('error', 'Unknown')}', 'e')
            return
    except RequestException as e:
        Stamp(f'Error during request: {e}')
        return


def setProxyComment(user_id, proxy_id, comment):
    Stamp(f'Setting comment "{comment}" for proxy ID {proxy_id}', 'i')
    try:
        response = get(URL_SET_COMMENT_PROXY + f'ids={proxy_id}&new={comment}')
        data = response.json()
        if data['status'] == 'yes':
            Stamp(f'Comment "{comment}" successfully set for proxy ID {proxy_id}', 's')
            BOT.send_message(user_id, f'🟩 Комментарий "{comment}" успешно установлен для прокси {proxy_id}')
        else:
            Stamp(f'Error when setting comment for proxy {proxy_id}: {data.get("error", "Unknown")}', 'e')
            BOT.send_message(user_id, f'🟥 Ошибка при установке комментария для прокси {proxy_id}: {data.get("error", "Unknown")}')
    except RequestException as e:
        Stamp(f'Error during set comment request: {e}', 'e')
        BOT.send_message(user_id, f'🟥 Ошибка при выполнении запроса на установку комментария для прокси {proxy_id}: {e}')

