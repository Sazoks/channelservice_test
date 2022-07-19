from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    """Модель данных о заказе"""

    number = models.PositiveIntegerField(
        unique=True,
        verbose_name=_('Номер записи'),
    )
    order_number = models.PositiveIntegerField(
        unique=True,
        verbose_name=_('Номер заказа'),
    )
    dollars = models.DecimalField(
        max_digits=18,
        decimal_places=5,
        validators=(MinValueValidator(0), ),
        verbose_name=_('Доллары США'),
    )
    delivery_time = models.DateField(
        verbose_name=_('Срок поставки'),
    )
    rubles = models.DecimalField(
        max_digits=18,
        decimal_places=5,
        validators=(MinValueValidator(0), ),
        verbose_name=_('Рубли РФ'),
    )

    class Meta:
        """Настройки модели"""

        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ('delivery_time', )

    def __str__(self) -> str:
        """Строковое представление объекта"""

        return f'Заказ#{self.order_number}'
