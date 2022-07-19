from celery import shared_task

from .observers import OrderObserver


@shared_task
def observe_order(spreadsheet_id: str, range_name: str) -> None:
    """
    Задание на мониторинг и обработку указанной Google Sheet.

    :param spreadsheet_id: id таблицы в Google Sheets.
    :param range_name:
        Диапазон ячеек, из которых необходимо считывать значения.
    """

    observer = OrderObserver(spreadsheet_id, range_name)
    observer.run()
