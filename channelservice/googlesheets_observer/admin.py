from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Класс администрации данных о заказах"""

    list_display = ('order_number', 'delivery_time',
                    'dollars', 'rubles')
    list_display_links = ('order_number', )
