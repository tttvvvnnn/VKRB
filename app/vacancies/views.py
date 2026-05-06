from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile
from resumes.models import Resume
from .forms import VacancyApplicationForm, VacancyForm
from .models import Vacancy, VacancyApplication


def get_user_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def user_is_recruiter(user):
    profile = get_user_profile(user)
    return profile.role == Profile.Role.RECRUITER


@login_required
def vacancy_list_view(request):
    my_vacancies = Vacancy.objects.filter(owner=request.user)

    public_vacancies = Vacancy.objects.filter(
        visibility=Vacancy.Visibility.PUBLIC
    ).exclude(
        owner=request.user
    )

    return render(request, 'vacancies/vacancy_list.html', {
        'my_vacancies': my_vacancies,
        'public_vacancies': public_vacancies,
        'is_recruiter': user_is_recruiter(request.user),
    })


@login_required
def vacancy_create_view(request):
    if not user_is_recruiter(request.user):
        messages.error(request, 'Создавать вакансии может только пользователь с ролью рекрутера.')
        return redirect('vacancy_list')

    if request.method == 'POST':
        form = VacancyForm(request.POST)

        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.owner = request.user
            vacancy.save()

            messages.success(request, 'Вакансия успешно создана.')
            return redirect('vacancy_detail', pk=vacancy.pk)
    else:
        form = VacancyForm()

    return render(request, 'vacancies/vacancy_form.html', {
        'form': form,
        'title': 'Создание вакансии',
        'button_text': 'Создать вакансию'
    })


@login_required
def vacancy_detail_view(request, pk):
    vacancy = get_object_or_404(
        Vacancy.objects.filter(
            Q(owner=request.user) | Q(visibility=Vacancy.Visibility.PUBLIC)
        ),
        pk=pk
    )

    is_owner = vacancy.owner == request.user

    applications = None
    if is_owner:
        applications = vacancy.applications.select_related(
            'resume',
            'applicant'
        )

    return render(request, 'vacancies/vacancy_detail.html', {
        'vacancy': vacancy,
        'is_owner': is_owner,
        'applications': applications,
    })


@login_required
def vacancy_update_view(request, pk):
    if not user_is_recruiter(request.user):
        messages.error(request, 'Редактировать вакансии может только рекрутер.')
        return redirect('vacancy_list')

    vacancy = get_object_or_404(
        Vacancy,
        pk=pk,
        owner=request.user
    )

    if request.method == 'POST':
        form = VacancyForm(request.POST, instance=vacancy)

        if form.is_valid():
            form.save()

            messages.success(request, 'Вакансия успешно обновлена.')
            return redirect('vacancy_detail', pk=vacancy.pk)
    else:
        form = VacancyForm(instance=vacancy)

    return render(request, 'vacancies/vacancy_form.html', {
        'form': form,
        'title': 'Редактирование вакансии',
        'button_text': 'Сохранить изменения'
    })


@login_required
def vacancy_delete_view(request, pk):
    if not user_is_recruiter(request.user):
        messages.error(request, 'Удалять вакансии может только рекрутер.')
        return redirect('vacancy_list')

    vacancy = get_object_or_404(
        Vacancy,
        pk=pk,
        owner=request.user
    )

    if request.method == 'POST':
        vacancy.delete()

        messages.success(request, 'Вакансия успешно удалена.')
        return redirect('vacancy_list')

    return render(request, 'vacancies/vacancy_confirm_delete.html', {
        'vacancy': vacancy
    })


@login_required
def vacancy_apply_view(request, pk):
    vacancy = get_object_or_404(
        Vacancy,
        pk=pk,
        visibility=Vacancy.Visibility.PUBLIC
    )

    if vacancy.owner == request.user:
        messages.error(request, 'Нельзя откликнуться на собственную вакансию.')
        return redirect('vacancy_detail', pk=vacancy.pk)

    user_resumes = Resume.objects.filter(owner=request.user)

    if not user_resumes.exists():
        messages.error(request, 'Для отклика сначала необходимо создать резюме.')
        return redirect('resume_create')

    if request.method == 'POST':
        form = VacancyApplicationForm(request.POST, user=request.user)

        if form.is_valid():
            resume = form.cleaned_data['resume']

            already_exists = VacancyApplication.objects.filter(
                vacancy=vacancy,
                resume=resume,
                applicant=request.user
            ).exists()

            if already_exists:
                messages.error(request, 'Вы уже откликались на эту вакансию с выбранным резюме.')
                return redirect('vacancy_detail', pk=vacancy.pk)

            application = form.save(commit=False)
            application.vacancy = vacancy
            application.applicant = request.user
            application.save()

            messages.success(request, 'Отклик успешно отправлен.')
            return redirect('application_list')
    else:
        form = VacancyApplicationForm(user=request.user)

    return render(request, 'vacancies/vacancy_apply.html', {
        'vacancy': vacancy,
        'form': form,
    })


@login_required
def application_list_view(request):
    my_applications = VacancyApplication.objects.filter(
        applicant=request.user
    ).select_related(
        'vacancy',
        'resume'
    )

    received_applications = None

    if user_is_recruiter(request.user):
        received_applications = VacancyApplication.objects.filter(
            vacancy__owner=request.user
        ).select_related(
            'vacancy',
            'resume',
            'applicant'
        )

    return render(request, 'vacancies/application_list.html', {
        'my_applications': my_applications,
        'received_applications': received_applications,
        'is_recruiter': user_is_recruiter(request.user),
    })


@login_required
def application_status_update_view(request, pk, status):
    if request.method != 'POST':
        return redirect('application_list')

    application = get_object_or_404(
        VacancyApplication,
        pk=pk,
        vacancy__owner=request.user
    )

    available_statuses = [
        VacancyApplication.Status.NEW,
        VacancyApplication.Status.VIEWED,
        VacancyApplication.Status.ACCEPTED,
        VacancyApplication.Status.REJECTED,
    ]

    if status not in available_statuses:
        messages.error(request, 'Некорректный статус отклика.')
        return redirect('application_list')

    application.status = status
    application.save()

    messages.success(request, 'Статус отклика обновлён.')
    return redirect('application_list')


@login_required
def application_delete_view(request, pk):
    application = get_object_or_404(
        VacancyApplication,
        pk=pk,
        applicant=request.user
    )

    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Отклик отменён.')
        return redirect('application_list')

    return render(request, 'vacancies/application_confirm_delete.html', {
        'application': application
    })