from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ResumeForm
from .models import Resume


def user_can_view_resume(user, resume):
    if resume.owner == user:
        return True

    if resume.visibility == Resume.Visibility.PUBLIC:
        return True

    from vacancies.models import VacancyApplication

    return VacancyApplication.objects.filter(
        resume=resume,
        vacancy__owner=user
    ).exists()


@login_required
def resume_list_view(request):
    resumes = Resume.objects.filter(owner=request.user)

    return render(request, 'resumes/resume_list.html', {
        'resumes': resumes
    })


@login_required
def resume_create_view(request):
    if request.method == 'POST':
        form = ResumeForm(request.POST)

        if form.is_valid():
            resume = form.save(commit=False)
            resume.owner = request.user
            resume.save()

            messages.success(request, 'Резюме успешно создано.')
            return redirect('resume_detail', pk=resume.pk)
    else:
        form = ResumeForm()

    return render(request, 'resumes/resume_form.html', {
        'form': form,
        'title': 'Создание резюме',
        'button_text': 'Создать резюме'
    })


@login_required
def resume_detail_view(request, pk):
    resume = get_object_or_404(Resume, pk=pk)

    if not user_can_view_resume(request.user, resume):
        raise Http404('Резюме недоступно для просмотра.')

    return render(request, 'resumes/resume_detail.html', {
        'resume': resume,
        'is_owner': resume.owner == request.user,
    })


@login_required
def resume_update_view(request, pk):
    resume = get_object_or_404(
        Resume,
        pk=pk,
        owner=request.user
    )

    if request.method == 'POST':
        form = ResumeForm(request.POST, instance=resume)

        if form.is_valid():
            form.save()

            messages.success(request, 'Резюме успешно обновлено.')
            return redirect('resume_detail', pk=resume.pk)
    else:
        form = ResumeForm(instance=resume)

    return render(request, 'resumes/resume_form.html', {
        'form': form,
        'title': 'Редактирование резюме',
        'button_text': 'Сохранить изменения'
    })


@login_required
def resume_delete_view(request, pk):
    resume = get_object_or_404(
        Resume,
        pk=pk,
        owner=request.user
    )

    if request.method == 'POST':
        resume.delete()

        messages.success(request, 'Резюме успешно удалено.')
        return redirect('resume_list')

    return render(request, 'resumes/resume_confirm_delete.html', {
        'resume': resume
    })