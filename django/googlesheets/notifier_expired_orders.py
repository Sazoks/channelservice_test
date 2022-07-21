import telebot
from typing import (
    Optional,
    Collection,
    List,
)
from django.conf import settings


from .models import Order


class NotifierExpiredOrders:
    """
    Класс уведомителя о просроченных заказах в Telegram.

    Принимает не вход коллекцию заказов и строит по ним отчет.
    """

    def __init__(self, expired_orders: Optional[Collection[Order]] = None) -> None:
        """Инициализатор класса"""

        self.__access_user_id: List[str] = settings.TELEGRAM_ACCESS_USER_ID
        self.__bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
        self.__expired_orders: List[Order] = expired_orders \
            if expired_orders is not None else []

    def send_report(self) -> None:
        """Формирование и отправка отчета о просроченных заказах"""

        if len(self.__expired_orders) > 0:
            # Формирование сообщения.
            message = 'Просроченные заказы:\n'
            for i, order in enumerate(self.__expired_orders):
                message += f'{i + 1}. ' \
                           f'Заказ#{order.order_number} ' \
                           f'Дата: {order.delivery_time} ' \
                           f'Цена: {order.dollars}\n'

            # Отправка сообщений.
            for user_id in self.__access_user_id:
                self.__bot.send_message(user_id, message)

    def add_order(self, expired_order: Order) -> None:
        """
        Добавление нового заказа к списку просроченных.

        :param expired_order: Объект заказа.
        """

        self.__expired_orders.append(expired_order)

    def remove_order(self, order: Order) -> None:
        """
        Удаление объекта заказа из списка просроченных.

        :param order: Объект заказа.
        """

        self.__expired_orders.remove(order)
