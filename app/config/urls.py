from django.contrib import admin
from django.urls import include, path

from accounts.views import home_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('resumes/', include('resumes.urls')),
    path('vacancies/', include('vacancies.urls')),
    path('matching/', include('matching.urls')),
]