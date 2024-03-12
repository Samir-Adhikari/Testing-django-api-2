from django.urls import path
from .views import get_community

urlpatterns = [
    # Add other URL patterns if needed
    path('community/<str:country>/<str:city>/', get_community, name='get_community'),
]
