import httplib2
import requests
from enum import (
    IntEnum,
    auto,
)
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
from django.db import transaction
from django.db.models import QuerySet
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from .models import Order


class OrderObserver:
    """
    Класс для мониторинга и обработки заказов из Google Sheets.

    Алгоритм работы:
        1. При инициализации настраивает объект сервисного аккаунта,
        через который происходит общение с API Google Sheets.
        2. Делает запрос всех значений на указанную таблицу.
        3. Формирует список валют под каждую уникальную дату из таблицы.
        4. Создает список объектов заказов.
        5. Удаляет все заказы из БД и записывает новые заказы, все в одной
        транзакции.
    """

    class ColumnIndex(IntEnum):
        """Индексы столбцов таблицы"""

        NUMBER = 0
        ORDER_NUMBER = auto()
        DOLLARS = auto()
        DELIVERY_TIME = auto()

    def __init__(self, spreadsheet_id: str, range_name: str) -> None:
        """
        Инициализатор класса.

        :param spreadsheet_id: id таблицы в Google Sheets.
        :param range_name:
            Диапазон ячеек, из которых необходимо считывать значения.
        """

        # Шаблон URL для получения валют. Для запроса необходимо подставить
        # через .format() дату формата dd/mm/yy.
        self.__cbr_currencies_url: str = config('CBR_CURRENCIES_URL')

        # Настройка параметров для работы с Google Cloud.
        self.__gs_scopes: str = config('GS_SCOPES')
        self.__gs_spreadsheet_id = spreadsheet_id
        self.__gs_range_name = range_name

        # Автоматически настраиваем все объекты http. Без этого аутентификация
        # в Google Cloud из Celery-воркера не работает.
        httplib2shim.patch()

        # Получаем объект сервисного аккаунта для работы с API.
        self.__service = self._create_service_account()

    def run(self) -> None:
        """Запуск обработчика таблицы"""

        # FIXME: Оптимизировать логику работы с БД.
        #  - удалять дубликаты дат, формировать список валют под каждую
        #  уникальную дату. Это уменьшит число запросов к API ЦБ.
        # FIXME: Добавить обработку исключений при создании объектов заказов
        #  и при отправке запроса на создание в БД.

        # Делаем запрос к указанной таблице на указанный диапазон.
        result: Dict[str, Any] = self.__service.spreadsheets().values().get(
            spreadsheetId=self.__gs_spreadsheet_id,
            range=self.__gs_range_name,
        ).execute()

        # Получаем данные из таблицы.
        data: Optional[List[List[str]]] = result.get('values', None)
        if data is None:
            # TODO: Сделать логирование.
            return

        # Удаляем заголовки из данных. Они не нужны.
        data.pop(0)

        # Многие даты в данных повторяются. Делать запрос к API ЦБ ради
        # повторных данных очень неэффективно. Сделаем запросы к API ЦБ только
        # для уникальных дат.
        date_to_dollars_dict = self._create_date_to_dollars_dict(data)

        # Создаем новые объекты заказов из таблицы.
        updated_orders = []
        for row in data:
            delivery_time = datetime.strptime(
                row[self.ColumnIndex.DELIVERY_TIME], '%d.%m.%Y'
            ).date()
            new_order = Order(
                number=int(row[self.ColumnIndex.NUMBER]),
                order_number=int(row[self.ColumnIndex.ORDER_NUMBER]),
                dollars=Decimal(row[self.ColumnIndex.DOLLARS]),
                delivery_time=delivery_time,
                rubles=Decimal(row[self.ColumnIndex.DOLLARS])
                       * date_to_dollars_dict[delivery_time]
            )
            updated_orders.append(new_order)

        # Обновляем данные в одной транзакции.
        with transaction.atomic():
            Order.objects.all().delete()
            Order.objects.bulk_create(updated_orders)

    def _create_service_account(self):
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

    def _create_date_to_dollars_dict(self, data: List[List[str]]) \
            -> Dict[datetime.date, Decimal]:
        """
        Создание словаря, который сопоставляет уникальные даты и курс
        доллара к каждой дате.

        :param data: Данные о заказах.
        :return: Словарь с датой и курсом доллара за эту дату.
        """

        # Получаем все уникальные даты среди всех данных.
        unique_dates = set([
            datetime.strptime(row[self.ColumnIndex.DELIVERY_TIME], '%d.%m.%Y').date()
            for row in data
        ])

        # Сделаем запрос к API ЦБ для каждой даты и узнам курсы доллара.
        dollars_per_day = [
            self._get_dollars_to_rubs(date) for date in unique_dates
        ]

        # Создадим словарь, который сопоставляет день и курс доллара
        # за этот день.
        result = dict(zip(unique_dates, dollars_per_day))

        return result

    def _get_dollars_to_rubs(self, date: datetime.date) -> Decimal:
        """
        Получение курса доллара к рублю на указанный день.

        :param date: День, за который нужно получить курс доллара.
        :return: Объект Decimal с точным значением курса доллара к рублю.
        """

        # Получаем сегодняшнюю дату и переводим в нужный формат.
        date_for_request = date.strftime('%d/%m/%Y')
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
