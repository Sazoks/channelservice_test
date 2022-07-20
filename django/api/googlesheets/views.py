from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import Sum

from googlesheets.models import Order
from .serializers import OrderSerializer


class OrdersAPIView(ListAPIView):
    """API для получения списка заказов"""

    http_method_names = ('get', )
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Получение списка заказов и суммы всех заказов в долларах"""

        # Получим объект ответа с сериализованным списком заказов.
        response = super(OrdersAPIView, self).get(request, *args, **kwargs)

        # Вычислим общую сумму заказов в долларах и добавим в ответ.
        total_dollars = self.get_queryset().aggregate(Sum('dollars'))['dollars__sum']
        data = {
            'total_dollars': total_dollars,
            'orders': response.data,
        }

        return Response(data=data)
