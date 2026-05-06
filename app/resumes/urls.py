from django.urls import path

from . import views


urlpatterns = [
    path('', views.resume_list_view, name='resume_list'),
    path('create/', views.resume_create_view, name='resume_create'),
    path('<int:pk>/', views.resume_detail_view, name='resume_detail'),
    path('<int:pk>/edit/', views.resume_update_view, name='resume_update'),
    path('<int:pk>/delete/', views.resume_delete_view, name='resume_delete'),
]