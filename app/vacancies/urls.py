from django.urls import path

from . import views

urlpatterns = [
    path('', views.vacancy_list_view, name='vacancy_list'),
    path('create/', views.vacancy_create_view, name='vacancy_create'),

    path('applications/', views.application_list_view, name='application_list'),
    path(
        'applications/<int:pk>/status/<str:status>/',
        views.application_status_update_view,
        name='application_status_update'
    ),
    path(
        'applications/<int:pk>/delete/',
        views.application_delete_view,
        name='application_delete'
    ),

    path('import/hh/', views.hh_import_view, name='hh_import'),
    path('import/trudvsem/', views.trudvsem_import_view, name='trudvsem_import'),

    path('<int:pk>/', views.vacancy_detail_view, name='vacancy_detail'),
    path('<int:pk>/edit/', views.vacancy_update_view, name='vacancy_update'),
    path('<int:pk>/delete/', views.vacancy_delete_view, name='vacancy_delete'),
    path('<int:pk>/apply/', views.vacancy_apply_view, name='vacancy_apply'),
]