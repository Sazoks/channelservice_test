from rest_framework.serializers import ModelSerializer

from googlesheets_observer.models import Order


class OrderSerializer(ModelSerializer):
    """Сериализатор модели заказа"""

    class Meta:
        """Класс настроек"""

        model = Order
        fields = '__all__'
