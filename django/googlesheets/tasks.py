from datetime import datetime
from celery import shared_task

from .models import Order
from .order_observer import OrderObserver
from .notifier_expired_orders import NotifierExpiredOrders


@shared_task
def observe_order(spreadsheet_id: str, range_name: str) -> None:
    """
    Задание на мониторинг и обработку указанной Google Sheet.

    :param spreadsheet_id: id таблицы в Google Sheets.
    :param range_name:
        Диапазон ячеек, из которых необходимо считывать значения.
    """

    # Синхронизируем данные в Google-таблице с данными в БД.
    observer = OrderObserver(spreadsheet_id, range_name)
    observer.run()

    # Ищем все просроченные заказы и уведомляем об этом в Telegram.
    expired_orders = Order.objects.filter(
        delivery_time__lt=datetime.now().date())

    # Генерируем и отправляем отчет.
    notifier = NotifierExpiredOrders(expired_orders)
    notifier.send_report()
