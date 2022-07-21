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
    Set,
)
from decimal import Decimal
from decouple import config
from datetime import datetime
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from .models import Order


class OrderObserver:
    """
    Класс для мониторинга и обработки заказов из Google Sheets.

    Алгоритм работы:
        1. Получает все данные из таблицы.
        2. Формирует из данных словарь, чтобы можно было получать данные о
        каком-либо заказе по номеру этого заказа.
        3. Формирует множества номеров заказов для удаления, обновления
        и создания:
            - заказы, которые есть и в таблице, и в БД, могут быть обновлены;
            - заказы, которые есть только в БД, должны быть удалены;
            - заказы, которые есть только в таблице, должны быть добавлены.
        4. Удаляет заказы, которые нужно удалить.
        5. Получает курс доллара на текущий день.
        6. Обновляет только те записи, которые действительно изменились.
        7. Создает новые записи и добавляет их в БД.
    """

    class ColumnIndex(IntEnum):
        """Индексы столбцов в Google-таблице"""

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

        # Делаем запрос к указанной таблице на указанный диапазон.
        result: Dict[str, Any] = self.__service.spreadsheets().values().get(
            spreadsheetId=self.__gs_spreadsheet_id,
            range=self.__gs_range_name,
        ).execute()

        # Получаем данные из таблицы.
        data: Optional[List[List[str]]] = result.get('values', None)
        if data is None:
            return

        # Удаляем заголовки из данных. Они не нужны.
        data.pop(0)

        # Создадим словарь, где ключ - номер заказа, значение - данные.
        # Для удобства получения данных из таблицы по номеру заказа.
        data_dict = self._create_orders_dict(data)

        # Создадим множества номеров заказов из БД и из таблицы.
        all_order_numbers = set(Order.objects.values_list('order_number', flat=True))
        google_order_numbers = set(data_dict.keys())

        # Получим множества номеров заказов для удаления, обновления и создания.
        deleting_order_numbers = all_order_numbers.difference(google_order_numbers)
        updating_order_numbers = all_order_numbers.intersection(google_order_numbers)
        new_order_numbers = google_order_numbers.difference(all_order_numbers)

        # Получим курс доллара за сегодняшний день.
        dollars_to_rubles = self._get_dollars_to_rubs()

        # Все делаем в рамках одной транзакции.
        with transaction.atomic():
            # Сначала удалим заказы, которых нет в Google таблице.
            Order.objects.filter(order_number__in=deleting_order_numbers).delete()

            # Обновление заказов, которые нужно обновить.
            self._update_orders(
                data_dict,
                updating_order_numbers,
                dollars_to_rubles,
            )

            # Создаем новые заказы.
            self._create_orders(
                data_dict,
                new_order_numbers,
                dollars_to_rubles,
            )

    def _update_orders(
            self,
            data_dict: Dict[int, List[str]],
            updating_order_numbers: Set[int],
            dollars_to_rubles: Decimal,
    ) -> None:
        """
        Обновление заказов.

        Обновляет только те заказы, у которых изменились данные.

        :param data_dict: Словарь с данными из Google-таблицы.
        :param updating_order_numbers:
            Множество id заказов, которые, возможно, нужно обновить.
        :param dollars_to_rubles: Курс доллара к рублю.
        """

        updating_orders = Order.objects \
            .filter(order_number__in=updating_order_numbers)

        for order in updating_orders:
            # Получим табличные значения.
            table_number = int(
                data_dict[order.order_number][self.ColumnIndex.NUMBER])
            table_dollars = Decimal(
                data_dict[order.order_number][self.ColumnIndex.DOLLARS])
            table_date = datetime.strptime(
                data_dict[order.order_number]
                [self.ColumnIndex.DELIVERY_TIME],
                '%d.%m.%Y',
            ).date()

            # Обновляем данные, если нужно.
            if order.number != table_number:
                order.number = table_number

            if order.dollars != table_dollars \
                    or order.delivery_time != table_date:
                # Обновим все значения.
                order.dollars = table_dollars
                order.delivery_time = table_date

            # В любом случае для каждой старой записи обновляем рубли,
            # т.к. курс на сегодня мог измениться.
            order.rubles = table_dollars * dollars_to_rubles

        # Обновляем заказы.
        Order.objects.bulk_update(
            updating_orders,
            ['number', 'dollars', 'delivery_time', 'rubles'],
        )

    def _create_orders(
            self,
            data_dict: Dict[int, List[str]],
            new_order_numbers: Set[int],
            dollars_to_rubles: Decimal,
    ) -> None:
        """
        Добавление новых заказов.

        :param data_dict: Словарь с данными из Google-таблицы.
        :param new_order_numbers: Множество id новых заказов.
        :param dollars_to_rubles: Курс доллара к рублю.
        """

        # Создаем новые объекты заказов из таблицы.
        new_orders: List[Order] = []

        for new_order_number in new_order_numbers:
            # Получим табличные значения.
            table_number = int(
                data_dict[new_order_number][self.ColumnIndex.NUMBER])
            table_order_number = int(
                data_dict[new_order_number][self.ColumnIndex.ORDER_NUMBER])
            table_dollars = Decimal(
                data_dict[new_order_number][self.ColumnIndex.DOLLARS])
            table_date = datetime.strptime(
                data_dict[new_order_number][self.ColumnIndex.DELIVERY_TIME],
                '%d.%m.%Y',
            ).date()
            new_rubles = table_dollars * dollars_to_rubles

            # Создаем новый заказ и добавляем в список.
            new_order = Order(
                number=table_number,
                order_number=table_order_number,
                dollars=table_dollars,
                delivery_time=table_date,
                rubles=new_rubles,
            )
            new_orders.append(new_order)

        # Добавляем новые заказы.
        Order.objects.bulk_create(new_orders)

    def _create_service_account(self):
        """
        Получение сервисного аккаунта в качестве ресурса.

        Необходим для работы с Google Cloud от лица сервисного аккаунта.
        """

        # Путь до файла с учетными данными сервисного аккаунта в json-формате.
        creds_json = settings.CREDS_DIR / settings.FILENAME_SERVICE_ACCOUNT_CREDS
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

    def _create_orders_dict(self, data: List[List[str]]) -> Dict[int, List[str]]:
        """
        Создание словаря с заказами.

        Ключ - номер заказа, значение - данные о заказе.
        Необходим для быстрого получения данных из таблицы по номеру заказа.

        :param data: Исходные данные.
        :return: Словарь с данными о заказах.
        """

        keys = [int(row[self.ColumnIndex.ORDER_NUMBER]) for row in data]
        result = dict(zip(keys, data))

        return result

    def _get_dollars_to_rubs(self) -> Decimal:
        """
        Получение курса доллара к рублю на сегодняшний день.

        :return: Объект Decimal с точным значением курса доллара к рублю.
        """

        # Переводим сегодняшнюю дату и переводим в нужный формат.
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
