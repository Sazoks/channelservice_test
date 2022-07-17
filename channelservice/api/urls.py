from django.urls import (
    path,
    include,
)

urlpatterns = [
    path('googlesheets-observer/', include('api.googlesheets_observer.urls')),
]
