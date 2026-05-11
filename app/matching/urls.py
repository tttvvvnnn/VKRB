from django.urls import path

from . import views


urlpatterns = [
    path('', views.matching_dashboard_view, name='matching_dashboard'),

    path('resume/<int:pk>/vacancies/', views.match_vacancies_for_resume_view, name='match_vacancies_for_resume'),
    path('vacancy/<int:pk>/resumes/',  views.match_resumes_for_vacancy_view,  name='match_resumes_for_vacancy'),

    path('job/<str:job_id>/poll/',   views.poll_job,   name='match_poll_job'),
    path('job/<str:job_id>/cancel/', views.cancel_job, name='match_cancel_job'),

    path('api/resume/<int:pk>/vacancies/', views.match_vacancies_for_resume_api, name='match_vacancies_for_resume_api'),
    path('api/vacancy/<int:pk>/resumes/',  views.match_resumes_for_vacancy_api,  name='match_resumes_for_vacancy_api'),
]