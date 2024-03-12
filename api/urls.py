from django.urls import path
from .views import get_community
from .views import get_communities
from .views import survey_statistics

urlpatterns = [
    # Add other URL patterns if needed
    path('community/<int:communityid>/', get_community, name='get_community'),
    path('communities', get_communities, name='get_communities'),
    path('surveys', survey_statistics, name='survey_statistics')
]
