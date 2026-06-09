from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import applicant_required, recruiter_required
from accounts.models import Profile
from resumes.models import Resume
from .forms import VacancyApplicationForm, VacancyFilterForm, VacancyForm
from .models import FavoriteVacancy, Vacancy, VacancyApplication


def _apply_live_filters(results, d):
    """Post-filter formatted live Trudvsem results based on filter form cleaned_data."""
    from .trudvsem_import import EMPLOYMENT_RU_TO_TYPE, SCHEDULE_RU_TO_TYPE

    _type_to_ru = {}
    for ru, t in {**EMPLOYMENT_RU_TO_TYPE, **SCHEDULE_RU_TO_TYPE}.items():
        _type_to_ru.setdefault(t, set()).add(ru)

    filtered = list(results)

    employment_types = d.get('employment_type')
    if employment_types:
        allowed_ru = set()
        for et in employment_types:
            allowed_ru |= _type_to_ru.get(et, set())
        filtered = [v for v in filtered if (v.get('employment') or '').lower() in allowed_ru]

    salary_min = d.get('salary_min')
    if salary_min:
        filtered = [v for v in filtered if v.get('salary_from') is not None and v['salary_from'] >= salary_min]

    salary_max = d.get('salary_max')
    if salary_max:
        filtered = [v for v in filtered if v.get('salary_from') is not None and v['salary_from'] <= salary_max]

    if d.get('has_salary'):
        filtered = [v for v in filtered if v.get('salary_from') is not None]

    experience = d.get('experience')
    if experience == '0':
        filtered = [v for v in filtered if (v.get('experience') or 0) == 0]
    elif experience == '1':
        filtered = [v for v in filtered if (v.get('experience') or 0) <= 1]
    elif experience == '3':
        filtered = [v for v in filtered if (v.get('experience') or 0) <= 3]
    elif experience == '6':
        filtered = [v for v in filtered if (v.get('experience') or 0) <= 6]
    elif experience == '6+':
        filtered = [v for v in filtered if (v.get('experience') or 0) > 6]

    city = d.get('city')
    if city:
        city_lower = city.lower()
        filtered = [v for v in filtered if city_lower in (v.get('city') or '').lower()]

    skill = d.get('skill')
    if skill:
        skill_lower = skill.lower()
        filtered = [v for v in filtered if any(skill_lower in s.lower() for s in (v.get('skills') or []))]

    return filtered


def get_user_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def user_is_recruiter(user):
    return get_user_profile(user).role == Profile.Role.RECRUITER


@login_required
def vacancy_list_view(request):
    from .forms import EXPERIENCE_CHOICES, SORT_CHOICES
    filter_form = VacancyFilterForm(request.GET or None)

    my_vacancies = Vacancy.objects.filter(owner=request.user).prefetch_related('skill_tags')
    public_vacancies = Vacancy.objects.filter(
        visibility=Vacancy.Visibility.PUBLIC
    ).exclude(owner=request.user).prefetch_related('skill_tags')

    # Distinct cities for hint
    cities = (
        Vacancy.objects.filter(visibility=Vacancy.Visibility.PUBLIC)
        .exclude(city='').exclude(city__isnull=True)
        .values_list('city', flat=True).distinct().order_by('city')[:60]
    )

    sort_order = '-created_at'

    if filter_form.is_valid():
        d = filter_form.cleaned_data

        search = d.get('search')
        if search:
            q = Q(title__icontains=search) | Q(company__icontains=search) | Q(description__icontains=search)
            public_vacancies = public_vacancies.filter(q)
            my_vacancies = my_vacancies.filter(q)

        employment_types = d.get('employment_type')
        if employment_types:
            public_vacancies = public_vacancies.filter(employment_type__in=employment_types)
            my_vacancies = my_vacancies.filter(employment_type__in=employment_types)

        city = d.get('city')
        if city:
            public_vacancies = public_vacancies.filter(city__icontains=city)
            my_vacancies = my_vacancies.filter(city__icontains=city)

        salary_min = d.get('salary_min')
        if salary_min:
            public_vacancies = public_vacancies.filter(salary_from__gte=salary_min)
            my_vacancies = my_vacancies.filter(salary_from__gte=salary_min)

        salary_max = d.get('salary_max')
        if salary_max:
            public_vacancies = public_vacancies.filter(
                Q(salary_to__lte=salary_max) | Q(salary_from__lte=salary_max)
            )
            my_vacancies = my_vacancies.filter(
                Q(salary_to__lte=salary_max) | Q(salary_from__lte=salary_max)
            )

        if d.get('has_salary'):
            public_vacancies = public_vacancies.filter(salary_from__isnull=False)
            my_vacancies = my_vacancies.filter(salary_from__isnull=False)

        experience = d.get('experience')
        if experience == '0':
            public_vacancies = public_vacancies.filter(required_experience_years=0)
            my_vacancies = my_vacancies.filter(required_experience_years=0)
        elif experience == '1':
            public_vacancies = public_vacancies.filter(required_experience_years__lte=1)
            my_vacancies = my_vacancies.filter(required_experience_years__lte=1)
        elif experience == '3':
            public_vacancies = public_vacancies.filter(required_experience_years__lte=3)
            my_vacancies = my_vacancies.filter(required_experience_years__lte=3)
        elif experience == '6':
            public_vacancies = public_vacancies.filter(required_experience_years__lte=6)
            my_vacancies = my_vacancies.filter(required_experience_years__lte=6)
        elif experience == '6+':
            public_vacancies = public_vacancies.filter(required_experience_years__gt=6)
            my_vacancies = my_vacancies.filter(required_experience_years__gt=6)

        skill = d.get('skill')
        if skill:
            public_vacancies = public_vacancies.filter(skill_tags__name__icontains=skill).distinct()
            my_vacancies = my_vacancies.filter(skill_tags__name__icontains=skill).distinct()

        if d.get('with_source'):
            public_vacancies = public_vacancies.exclude(source_url='')
            my_vacancies = my_vacancies.exclude(source_url='')

        if d.get('only_local'):
            public_vacancies = public_vacancies.filter(source_url='')
            my_vacancies = my_vacancies.filter(source_url='')

        sort_order = d.get('sort_by') or '-created_at'

    public_vacancies = public_vacancies.order_by(sort_order)
    public_page = Paginator(public_vacancies, 12).get_page(request.GET.get('page'))

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query = filter_params.urlencode()

    active_filters = sum(1 for k, v in request.GET.items() if v and k not in ('page', 'sort_by'))

    directions = [
        'IT / Разработка', 'Аналитика / Data', 'DevOps', 'QA / Тестирование',
        'Дизайн', 'Маркетинг', 'Продажи', 'Финансы', 'HR', 'Образование',
        'Медицина', 'Юриспруденция',
    ]

    # ── Live trudvsem results (first 2 pages = 24 results) ───────────────────
    from .trudvsem_import import _vac_uid, city_to_region_code, format_live_item, live_search

    live_filters = filter_form.cleaned_data if filter_form.is_valid() else {}
    only_local   = live_filters.get('only_local', False)
    search_query = live_filters.get('search', '')
    city_text    = live_filters.get('city', '')
    region_code  = city_to_region_code(city_text)

    from django.core.cache import cache

    live_results = []
    live_total   = 0
    live_error   = None
    if not only_local:
        try:
            items1, live_total = live_search(search_query, region_code, offset=0,  per_page=12)
            items2, _          = live_search(search_query, region_code, offset=12, per_page=12)
            raw_items = items1 + items2
            for raw in raw_items:
                uid = _vac_uid(raw)
                if uid:
                    cache.set(f'trudvsem_vac_{uid}', raw, 3600)
            live_results = _apply_live_filters([format_live_item(i) for i in raw_items], live_filters)
        except Exception as e:
            live_error = str(e)

    return render(request, 'vacancies/vacancy_list.html', {
        'my_vacancies': my_vacancies,
        'public_page':  public_page,
        'is_recruiter': user_is_recruiter(request.user),
        'filter_form': filter_form,
        'filter_query': filter_query,
        'cities': list(cities),
        'active_filters': active_filters,
        'directions': directions,
        # live trudvsem
        'live_results': live_results,
        'live_total':   live_total,
        'live_loaded':  len(live_results),
        'live_error':   live_error,
        'live_search':  search_query,
        'live_region':  region_code or '',
        'only_local':   only_local,
    })


@login_required
@recruiter_required
def vacancy_create_view(request):
    if request.method == 'POST':
        form = VacancyForm(request.POST)

        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.owner = request.user
            vacancy.save()
            form.save_m2m()

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
        ).prefetch_related('skill_tags'),
        pk=pk
    )

    is_owner = vacancy.owner == request.user
    is_favorited = FavoriteVacancy.objects.filter(user=request.user, vacancy=vacancy).exists()
    user_resumes = Resume.objects.filter(owner=request.user)

    applications = None
    if is_owner:
        applications = vacancy.applications.select_related('resume', 'applicant')

    return render(request, 'vacancies/vacancy_detail.html', {
        'vacancy': vacancy,
        'is_owner': is_owner,
        'is_favorited': is_favorited,
        'is_recruiter': user_is_recruiter(request.user),
        'user_resumes': user_resumes,
        'applications': applications,
    })


@login_required
@recruiter_required
def vacancy_update_view(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, owner=request.user)

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
@recruiter_required
def vacancy_delete_view(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, owner=request.user)

    if request.method == 'POST':
        vacancy.delete()

        messages.success(request, 'Вакансия успешно удалена.')
        return redirect('vacancy_list')

    return render(request, 'vacancies/vacancy_confirm_delete.html', {
        'vacancy': vacancy
    })


@login_required
@applicant_required
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
    ).select_related('vacancy', 'resume')

    received_applications = None

    if user_is_recruiter(request.user):
        received_applications = VacancyApplication.objects.filter(
            vacancy__owner=request.user
        ).select_related('vacancy', 'resume', 'applicant')

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
def trudvsem_vacancy_detail_view(request, vac_id):
    import logging
    from django.core.cache import cache
    from matching.services import calculate_match_quick
    from resumes.models import Resume as ResumeModel
    from .trudvsem_import import fetch_vacancy, format_vacancy_detail

    log = logging.getLogger(__name__)
    error = None
    vacancy = None

    item = cache.get(f'trudvsem_vac_{vac_id}')
    log.warning('TRUDVSEM DETAIL | vac_id=%s | cache_hit=%s | title=%s | vac_url=%s',
                vac_id, item is not None,
                (item or {}).get('job-name', '—'),
                (item or {}).get('vac_url', '—'))
    if not item:
        try:
            item = fetch_vacancy(vac_id)
        except Exception as e:
            error = str(e)

    if item:
        vacancy = format_vacancy_detail(item)
        if vacancy:
            from matching.services import extract_skills_from_text, resolve_skills_to_db
            # Map raw API skills to DB skills (filters out long phrases)
            api_skills_resolved = resolve_skills_to_db(vacancy.get('skills') or [], threshold=0.55)
            # Extract skills from vacancy text
            vacancy_text = ' '.join(filter(None, [
                vacancy.get('title', ''),
                vacancy.get('description', ''),
                vacancy.get('requirements', ''),
            ]))
            text_skills = extract_skills_from_text(vacancy_text)
            # Merge deduplicated
            seen = {s.lower() for s in api_skills_resolved}
            merged = list(api_skills_resolved)
            for s in text_skills:
                if s.lower() not in seen:
                    seen.add(s.lower())
                    merged.append(s)
            vacancy['skills'] = merged
    elif not error:
        error = 'Вакансия не найдена. Вернитесь в список и откройте её снова.'

    is_favorited = FavoriteVacancy.objects.filter(user=request.user, trudvsem_uid=vac_id).exists()
    user_resumes = ResumeModel.objects.filter(owner=request.user)
    return render(request, 'vacancies/trudvsem_vacancy_detail.html', {
        'vacancy': vacancy,
        'error': error,
        'vac_id': vac_id,
        'is_favorited': is_favorited,
        'user_resumes': user_resumes,
    })


@login_required
def trudvsem_load_more(request):
    """AJAX endpoint: returns next page of live trudvsem results as JSON."""
    from .trudvsem_import import _vac_uid, city_to_region_code, format_live_item, live_search
    from django.core.cache import cache
    from django.http import JsonResponse

    filter_form  = VacancyFilterForm(request.GET)
    live_filters = filter_form.cleaned_data if filter_form.is_valid() else {}

    search      = live_filters.get('search') or ''
    city_text   = live_filters.get('city') or ''
    region_code = city_to_region_code(city_text) or request.GET.get('region_code') or None

    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except ValueError:
        offset = 0

    try:
        items, total = live_search(search, region_code, offset=offset, per_page=12)
        for raw in items:
            uid = _vac_uid(raw)
            if uid:
                cache.set(f'trudvsem_vac_{uid}', raw, 3600)
        results = _apply_live_filters([format_live_item(i) for i in items], live_filters)
        return JsonResponse({'results': results, 'total': total, 'offset': offset, 'count': len(results)})
    except Exception as e:
        return JsonResponse({'error': str(e), 'results': [], 'total': 0}, status=500)


@login_required
@recruiter_required
def hh_import_view(request):
    from .hh_import import HH_AREAS, import_from_hh

    context = {'areas': HH_AREAS, 'done': False}

    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        area  = request.POST.get('area', '')
        try:
            count = max(1, min(20, int(request.POST.get('count') or 10)))
        except ValueError:
            count = 10

        if not query:
            messages.error(request, 'Введите поисковый запрос.')
            return render(request, 'vacancies/hh_import.html', context)

        try:
            imported, skipped, errors = import_from_hh(query, area, count, request.user)
            context.update({
                'done': True,
                'imported': imported,
                'skipped': skipped,
                'errors': errors,
                'query': query,
            })
        except Exception as e:
            messages.error(request, f'Ошибка при обращении к hh.ru: {e}')

    return render(request, 'vacancies/hh_import.html', context)


@login_required
@recruiter_required
def trudvsem_import_view(request):
    from .trudvsem_import import TRUDVSEM_REGIONS, import_from_trudvsem

    context = {'regions': TRUDVSEM_REGIONS, 'done': False}

    if request.method == 'POST':
        query       = request.POST.get('query', '').strip()
        region_code = request.POST.get('region_code', '')
        try:
            count = max(1, min(100, int(request.POST.get('count') or 10)))
        except ValueError:
            count = 10

        try:
            imported, skipped, errors = import_from_trudvsem(query, region_code, count, request.user)
            context.update({
                'done': True,
                'imported': imported,
                'skipped': skipped,
                'errors': errors,
                'query': query,
            })
        except Exception as e:
            messages.error(request, f'Ошибка при обращении к Труд Всем: {e}')

    return render(request, 'vacancies/trudvsem_import.html', context)


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


# ── Favorites ─────────────────────────────────────────────────────────────────

@login_required
def toggle_favorite_vacancy(request, pk):
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    vacancy = get_object_or_404(Vacancy, pk=pk)
    fav = FavoriteVacancy.objects.filter(user=request.user, vacancy=vacancy).first()
    if fav:
        fav.delete()
        return JsonResponse({'favorited': False})
    FavoriteVacancy.objects.create(user=request.user, vacancy=vacancy)
    return JsonResponse({'favorited': True})


@login_required
def toggle_favorite_trudvsem(request, vac_id):
    from django.core.cache import cache
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    fav = FavoriteVacancy.objects.filter(user=request.user, trudvsem_uid=vac_id).first()
    if fav:
        fav.delete()
        return JsonResponse({'favorited': False})
    item = cache.get(f'trudvsem_vac_{vac_id}') or {}
    FavoriteVacancy.objects.create(user=request.user, trudvsem_uid=vac_id, trudvsem_data=item)
    return JsonResponse({'favorited': True})


# ── On-demand AI score ─────────────────────────────────────────────────────────

@login_required
def ai_score_vacancy(request, pk):
    from django.http import JsonResponse
    from matching.services import calculate_match
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    vacancy = get_object_or_404(Vacancy, pk=pk)
    resume_pk = request.POST.get('resume_id')
    resume = get_object_or_404(Resume, pk=resume_pk, owner=request.user)
    try:
        result = calculate_match(resume, vacancy)
        if not result.get('ai_used'):
            return JsonResponse({'error': 'Groq AI недоступен (нет ключа)'}, status=503)
        return JsonResponse({
            'score_percent': round(result['score_percent']),
            'explanation': result['explanation'],
            'relevant_experience_years': result.get('relevant_experience_years'),
            'matched_skills': result['matched_skills'],
            'missing_skills': result['missing_skills'],
            'breakdown': result.get('breakdown', []),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ai_score_trudvsem(request, vac_id):
    from django.core.cache import cache
    from django.http import JsonResponse
    from matching.services import calculate_match_live
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    resume_pk = request.POST.get('resume_id')
    resume = get_object_or_404(Resume, pk=resume_pk, owner=request.user)
    vac_dict = cache.get(f'trudvsem_vac_{vac_id}')
    if not vac_dict:
        fav = FavoriteVacancy.objects.filter(user=request.user, trudvsem_uid=vac_id).first()
        if fav and fav.trudvsem_data:
            vac_dict = fav.trudvsem_data
    if not vac_dict:
        return JsonResponse({'error': 'Данные вакансии не найдены, откройте её снова'}, status=404)
    try:
        result = calculate_match_live(resume, vac_dict)
        if not result.get('ai_used'):
            return JsonResponse({'error': 'Groq AI недоступен (нет ключа)'}, status=503)
        return JsonResponse({
            'score_percent': round(result['score_percent']),
            'explanation': result['explanation'],
            'relevant_experience_years': result.get('relevant_experience_years'),
            'matched_skills': result['matched_skills'],
            'missing_skills': result['missing_skills'],
            'breakdown': result.get('breakdown', []),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)