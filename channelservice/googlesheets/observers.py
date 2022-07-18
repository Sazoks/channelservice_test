import httplib2
import requests
from typing import (
    List,
    Dict,
    Any,
    Optional,
)
from decimal import Decimal
from decouple import config
from datetime import datetime
from bs4 import BeautifulSoup
from django.conf import settings
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


class OrderObserver:
    """
    Класс для мониторинга и обработки заказов из Google Sheets.

    Алгоритм работы:
        1. При инициализации настраивает объект сервисного аккаунта,
        через который происходит общение с API Google Sheets.
        2. Делает запрос всех занчений на указанную таблицу.
        3. Делает запрос к API ЦБ за курсом доллара к рублю на
        сегодняшний день.
        4. ...
    """

    def __init__(self) -> None:
        """Инициализатор класса"""

        # Настройка параметров для работы с Google Cloud.
        self.__gs_scopes: str = config('GS_SCOPES')
        self.__gs_spreadsheet_id: str = config('GS_SPREADSHEET_ID')
        self.__gs_range_name: str = config('GS_RANGE_NAME')

        # Шаблон URL для получения валют. Для запроса необходимо подставить
        # через .format() дату формата dd/mm/yy.
        self.__cbr_currencies_url: str = config('CBR_CURRENCIES_URL')

        # Получаем объект сервисного аккаунта для работы с API.
        self.__service = self._get_service_account()

    def run(self) -> None:
        """Запуск обработчика таблицы"""

        # Делаем запрос к указанной таблице на указанный диапазон.
        result: Dict[str, Any] = self.__service.spreadsheets().values().get(
            spreadsheetId=self.__gs_spreadsheet_id,
            range=self.__gs_range_name,
        ).execute()

        # Получаем строки таблицы.
        values: Optional[List[List[str]]] = result.get('values', None)
        if values is None:
            ...

        # Получаем курс доллара к рублю на сегодняшний день.
        dollars_to_rubs = self._get_dollars_to_rubs()

    def _get_service_account(self):
        """
        Получение сервисного аккаунта в качестве ресурса.

        Необходим для работы с Google Cloud от лица сервисного аккаунта.
        """

        # Путь до файла с учетными данными сервисного аккаунта в json-формате.
        creds_json = settings.BASE_DIR / 'creds/creds.json'
        # Список необходимых разрешений на работу с каким-либо API.
        # В нашем случае - с Google Sheets.
        scopes = (self.__gs_scopes, )

        # Создание учетных данных сервисного аккаунта.
        creds_service = ServiceAccountCredentials \
            .from_json_keyfile_name(creds_json, scopes) \
            .authorize(httplib2.Http())
        # Создание объекта подключения к облаку на основе учетных данных
        # сервисного аккаунта.
        service = build(serviceName='sheets', version='v4', http=creds_service)

        return service

    def _get_dollars_to_rubs(self) -> Decimal:
        """
        Получение курса доллара к рублю на сегодняшний день.

        :return: Объект Decimal с точным значением курса доллара к рублю.
        """

        # Получаем сегодняшнюю дату и переводим в нужный формат.
        date_for_request = datetime.now().date().strftime('%d/%m/%Y')
        # Делаем запрос к API ЦБ.
        response = requests.get(self.__cbr_currencies_url.format(date_for_request))

        # Получаем тело xml-документ.
        xml_content = response.content
        # Строим DOM-дерево и парсим значение доллара.
        root = BeautifulSoup(xml_content, 'xml')
        dollars_to_rubs = Decimal(
            root.find('Valute', attrs={'ID': 'R1235'})
                .find('Value').text.replace(',', '.')
        )

        return dollars_to_rubs
