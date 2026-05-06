from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from accounts.models import Profile
from resumes.models import Resume
from vacancies.models import Vacancy
from .services import rank_resumes_for_vacancy, rank_vacancies_for_resume


def user_is_recruiter(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role == Profile.Role.RECRUITER


@login_required
def matching_dashboard_view(request):
    my_resumes = Resume.objects.filter(owner=request.user)
    my_vacancies = Vacancy.objects.filter(owner=request.user)

    return render(request, 'matching/dashboard.html', {
        'my_resumes': my_resumes,
        'my_vacancies': my_vacancies,
        'is_recruiter': user_is_recruiter(request.user),
    })


@login_required
def match_vacancies_for_resume_view(request, pk):
    resume = get_object_or_404(
        Resume,
        pk=pk,
        owner=request.user
    )

    vacancies = Vacancy.objects.filter(
        visibility=Vacancy.Visibility.PUBLIC
    ).exclude(
        owner=request.user
    )

    results = rank_vacancies_for_resume(resume, vacancies)

    return render(request, 'matching/vacancies_for_resume.html', {
        'resume': resume,
        'results': results,
    })


@login_required
def match_resumes_for_vacancy_view(request, pk):
    vacancy = get_object_or_404(
        Vacancy,
        pk=pk,
        owner=request.user
    )

    resumes = Resume.objects.filter(
        visibility=Resume.Visibility.PUBLIC,
        search_status__in=[
            Resume.SearchStatus.LOOKING,
            Resume.SearchStatus.OPEN_TO_OFFERS,
        ]
    ).exclude(
        owner=request.user
    )

    results = rank_resumes_for_vacancy(vacancy, resumes)

    return render(request, 'matching/resumes_for_vacancy.html', {
        'vacancy': vacancy,
        'results': results,
    })


@login_required
def match_vacancies_for_resume_api(request, pk):
    resume = get_object_or_404(
        Resume,
        pk=pk,
        owner=request.user
    )

    vacancies = Vacancy.objects.filter(
        visibility=Vacancy.Visibility.PUBLIC
    ).exclude(
        owner=request.user
    )

    results = rank_vacancies_for_resume(resume, vacancies)

    data = []
    for item in results:
        vacancy = item['vacancy']

        data.append({
            'vacancy_id': vacancy.id,
            'title': vacancy.title,
            'company': vacancy.company,
            'score_percent': item['score_percent'],
            'matched_skills': item['matched_skills'],
            'missing_skills': item['missing_skills'],
            'explanation': item['explanation'],
        })

    return JsonResponse({
        'resume_id': resume.id,
        'resume_title': resume.title,
        'results': data,
    })


@login_required
def match_resumes_for_vacancy_api(request, pk):
    vacancy = get_object_or_404(
        Vacancy,
        pk=pk,
        owner=request.user
    )

    resumes = Resume.objects.filter(
        visibility=Resume.Visibility.PUBLIC,
        search_status__in=[
            Resume.SearchStatus.LOOKING,
            Resume.SearchStatus.OPEN_TO_OFFERS,
        ]
    ).exclude(
        owner=request.user
    )

    results = rank_resumes_for_vacancy(vacancy, resumes)

    data = []
    for item in results:
        resume = item['resume']

        data.append({
            'resume_id': resume.id,
            'title': resume.title,
            'full_name': resume.full_name,
            'desired_position': resume.desired_position,
            'score_percent': item['score_percent'],
            'matched_skills': item['matched_skills'],
            'missing_skills': item['missing_skills'],
            'explanation': item['explanation'],
        })

    return JsonResponse({
        'vacancy_id': vacancy.id,
        'vacancy_title': vacancy.title,
        'results': data,
    })