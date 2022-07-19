from rest_framework.generics import ListAPIView

from googlesheets.models import Order
from .serializers import OrderSerializer


class OrdersAPIView(ListAPIView):
    """API для получения списка заказов"""

    http_method_names = ('get', )
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
