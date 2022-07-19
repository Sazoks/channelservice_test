import httplib2
import requests
import httplib2shim
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

from .models import Order


# FIXME: Вынести логику обновления курса валют в отдельную таску.
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

    def __init__(self, spreadsheet_id: str, range_name: str) -> None:
        """
        Инициализатор класса.

        :param spreadsheet_id: id таблицы в Google Sheets.
        :param range_name:
            Диапазон ячеек, из которых необходимо считывать значения.
        """

        # Настройка параметров для работы с Google Cloud.
        self.__gs_scopes: str = config('GS_SCOPES')
        self.__gs_spreadsheet_id = spreadsheet_id
        self.__gs_range_name = range_name

        # Шаблон URL для получения валют. Для запроса необходимо подставить
        # через .format() дату формата dd/mm/yy.
        self.__cbr_currencies_url: str = config('CBR_CURRENCIES_URL')

        httplib2shim.patch()
        # Получаем объект сервисного аккаунта для работы с API.
        self.__service = self._get_service_account()

    def run(self) -> None:
        """Запуск обработчика таблицы"""

        # Делаем запрос к указанной таблице на указанный диапазон.
        result: Dict[str, Any] = self.__service.spreadsheets().values().get(
            spreadsheetId=self.__gs_spreadsheet_id,
            range=self.__gs_range_name,
        ).execute()

        # Получаем данные из таблицы.
        # 1-й элемент - заголовки вида ['title_1', 'title_2', ...].
        # Остальные элементы - данные вида ['value_1', 'value_2', ...].
        data: Optional[List[List[str]]] = result.get('values', None)
        if data is None:
            # TODO: Сделать проверку данных.
            ...

        # Удаляем строку с заголовками.
        
        # Получаем только валидные данные. Их и будем записывать в БД.
        data = self._get_validated_data(data)

        # Получаем курс доллара к рублю на сегодняшний день.
        dollars_to_rubs = self._get_dollars_to_rubs()

        # FIXME: Исправить инициализацию.
        new_orders = [
            Order(
                number=int(row[0]),
                order_number=int(row[1]),
                dollars=float(row[2]),
                delivery_time=datetime.strptime(row[3], '%d.%m.%Y'),
                rubles=Decimal(float(row[2])) * dollars_to_rubs,
            )
            for i, row in enumerate(values) if i != 0
        ]
        print(new_orders)

        # TODO: Сделать проверки на удаленные строки, измененные строки,
        #  новые строки.
        Order.objects.bulk_create(new_orders)

    def _get_validated_data(self, data: List[List[str]]) -> List[List[str]]:
        """
        Метод валидации данных из таблицы.

        Создает новый список только с валидными строками таблицы.
        Валидная строка - строка, в которой каждое значение валидное.

        :param data: Исходные данные из таблицы.
        :return: Провалидированный список данных.
        """

        validated_data: List[List[str]] = []


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
            root.find('Valute', attrs={'ID': 'R01235'})
                .find('Value').text.replace(',', '.')
        )

        return dollars_to_rubs
