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

    path('trudvsem/more/', views.trudvsem_load_more, name='trudvsem_load_more'),
    path('trudvsem/<str:vac_id>/favorite/', views.toggle_favorite_trudvsem, name='toggle_favorite_trudvsem'),
    path('trudvsem/<str:vac_id>/ai-score/', views.ai_score_trudvsem, name='ai_score_trudvsem'),
    path('trudvsem/<str:vac_id>/', views.trudvsem_vacancy_detail_view, name='trudvsem_vacancy_detail'),
    path('import/hh/', views.hh_import_view, name='hh_import'),
    path('import/trudvsem/', views.trudvsem_import_view, name='trudvsem_import'),

    path('<int:pk>/favorite/', views.toggle_favorite_vacancy, name='toggle_favorite_vacancy'),
    path('<int:pk>/ai-score/', views.ai_score_vacancy, name='ai_score_vacancy'),
    path('<int:pk>/', views.vacancy_detail_view, name='vacancy_detail'),
    path('<int:pk>/edit/', views.vacancy_update_view, name='vacancy_update'),
    path('<int:pk>/delete/', views.vacancy_delete_view, name='vacancy_delete'),
    path('<int:pk>/apply/', views.vacancy_apply_view, name='vacancy_apply'),
]