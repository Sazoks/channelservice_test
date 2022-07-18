from django.urls import (
    path,
    include,
)

urlpatterns = [
    path('googlesheets/', include('api.googlesheets.urls')),
]
