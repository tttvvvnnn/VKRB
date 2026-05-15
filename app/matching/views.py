import threading
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import Profile
from resumes.models import Resume
from vacancies.models import Vacancy
from .services import calculate_match, calculate_match_live, rank_vacancies_for_resume, rank_resumes_for_vacancy

# { job_id: { done, error, cancel, total, partial: [...] } }
_jobs: dict = {}
_jobs_lock = threading.Lock()


def user_is_recruiter(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role == Profile.Role.RECRUITER


def _get_job(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else {}


def _cancel_job(job_id):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]['cancel'] = True


def _pop_job(job_id):
    with _jobs_lock:
        return _jobs.pop(job_id, None)


def _serialize_live_result(item):
    from vacancies.trudvsem_import import format_live_item
    f = format_live_item(item['vac_dict'])
    vac_id = item['vac_id']
    return {
        'vac_id':           vac_id,
        'title':            f['title'],
        'company':          f['company'],
        'city':             f['city'],
        'salary_from':      f['salary_from'],
        'salary_to':        f['salary_to'],
        'source_url':       f['source_url'],
        'detail_url':       f'/vacancies/trudvsem/{vac_id}/',
        'score_percent':    item['score_percent'],
        'progress_percent': item.get('progress_percent', 0),
        'ai_used':          item.get('ai_used', False),
        'explanation':      item.get('explanation', ''),
        'matched_skills':   item.get('matched_skills', []),
        'missing_skills':   item.get('missing_skills', []),
        'breakdown':        item.get('breakdown', []),
    }


def _serialize_vacancy_result(item):
    v = item['vacancy']
    return {
        'pk':             v.pk,
        'title':          v.title,
        'company':        v.company,
        'city':           v.city or '',
        'salary_from':    v.salary_from,
        'salary_to':      v.salary_to,
        'source_url':     getattr(v, 'source_url', ''),
        'score_percent':  item['score_percent'],
        'progress_percent': item.get('progress_percent', 0),
        'ai_used':        item.get('ai_used', False),
        'explanation':    item.get('explanation', ''),
        'matched_skills': item.get('matched_skills', []),
        'missing_skills': item.get('missing_skills', []),
        'breakdown':      item.get('breakdown', []),
    }


def _serialize_resume_result(item):
    r = item['resume']
    return {
        'pk':               r.pk,
        'title':            r.title,
        'full_name':        r.full_name or '',
        'desired_position': r.desired_position or '',
        'city':             r.city or '',
        'experience_years': float(r.experience_years or 0),
        'score_percent':    item['score_percent'],
        'progress_percent': item.get('progress_percent', 0),
        'ai_used':          item.get('ai_used', False),
        'explanation':      item.get('explanation', ''),
        'matched_skills':   item.get('matched_skills', []),
        'missing_skills':   item.get('missing_skills', []),
        'breakdown':        item.get('breakdown', []),
    }


def _run_vacancies_job(job_id, resume, vacancies):
    from django.db import connection
    partial = []
    try:
        for vacancy in vacancies:
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('cancel'):
                    break
            match_data = calculate_match(resume, vacancy)
            match_data['vacancy'] = vacancy
            partial.append(match_data)
            sorted_partial = sorted(partial, key=lambda x: x['score'], reverse=True)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]['partial'] = sorted_partial
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['done'] = True
    except Exception as e:
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['error'] = str(e)
                _jobs[job_id]['done'] = True
    finally:
        connection.close()


def _run_live_vacancies_job(job_id, resume_pk, vac_items):
    from django.db import connection
    partial = []
    try:
        resume = Resume.objects.prefetch_related('skill_tags').get(pk=resume_pk)
        for uid, vac_dict in vac_items:
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('cancel'):
                    break
            from vacancies.trudvsem_import import format_live_item
            match_data = calculate_match_live(resume, vac_dict)
            match_data['vac_id'] = uid
            match_data['vac_dict'] = vac_dict
            fmt = format_live_item(vac_dict)
            match_data.update({k: fmt[k] for k in ('title', 'company', 'city', 'salary_from', 'salary_to', 'source_url')})
            partial.append(match_data)
            sorted_partial = sorted(partial, key=lambda x: x['score'], reverse=True)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]['partial'] = sorted_partial
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['done'] = True
    except Exception as e:
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['error'] = str(e)
                _jobs[job_id]['done'] = True
    finally:
        connection.close()


def _run_resumes_job(job_id, vacancy, resumes):
    from django.db import connection
    partial = []
    try:
        for resume in resumes:
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('cancel'):
                    break
            match_data = calculate_match(resume, vacancy)
            match_data['resume'] = resume
            partial.append(match_data)
            sorted_partial = sorted(partial, key=lambda x: x['score'], reverse=True)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]['partial'] = sorted_partial
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['done'] = True
    except Exception as e:
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['error'] = str(e)
                _jobs[job_id]['done'] = True
    finally:
        connection.close()


def _start_job(job_id, target, *args):
    with _jobs_lock:
        _jobs[job_id] = {'done': False, 'cancel': False, 'error': '', 'partial': [], 'total': args[-1]}
    threading.Thread(target=target, args=(job_id,) + args[:-1], daemon=True).start()


# ── Poll / Cancel ──────────────────────────────────────────────────────────────

@login_required
def poll_job(request, job_id):
    job = _get_job(job_id)
    if not job:
        return JsonResponse({'done': True, 'error': 'Задача не найдена', 'results': [], 'computed': 0, 'total': 0})

    partial = job.get('partial', [])
    mode = request.GET.get('mode', 'vacancy')
    if mode == 'live':
        serializer = _serialize_live_result
    elif mode == 'resume':
        serializer = _serialize_resume_result
    else:
        serializer = _serialize_vacancy_result

    return JsonResponse({
        'done':     job.get('done', False),
        'cancel':   job.get('cancel', False),
        'error':    job.get('error', ''),
        'computed': len(partial),
        'total':    job.get('total', 0),
        'results':  [serializer(r) for r in partial],
    })


@login_required
def cancel_job(request, job_id):
    if request.method == 'POST':
        _cancel_job(job_id)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=405)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def matching_dashboard_view(request):
    my_resumes = Resume.objects.filter(owner=request.user)
    my_vacancies = Vacancy.objects.filter(owner=request.user)
    return render(request, 'matching/dashboard.html', {
        'my_resumes': my_resumes,
        'my_vacancies': my_vacancies,
        'is_recruiter': user_is_recruiter(request.user),
    })


# ── Vacancies for resume ───────────────────────────────────────────────────────

@login_required
def match_vacancies_for_resume_view(request, pk):
    resume = get_object_or_404(Resume, pk=pk, owner=request.user)
    job_id = request.GET.get('job_id', '')

    if job_id:
        job = _get_job(job_id)
        if job.get('done'):
            results = job.get('partial', [])
            _pop_job(job_id)
            return render(request, 'matching/vacancies_for_resume.html', {
                'resume': resume,
                'results': results,
                'error': job.get('error', ''),
            })
        # still running — computing page handles polling itself
        return render(request, 'matching/computing.html', {
            'subject':    resume.title,
            'total':      job.get('total', 0),
            'job_id':     job_id,
            'mode':       'vacancy',
            'cancel_url': reverse('match_cancel_job', args=[job_id]),
            'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=vacancy',
            'done_url':   request.path + f'?job_id={job_id}',
        })

    vacancies = list(
        Vacancy.objects
        .filter(visibility=Vacancy.Visibility.PUBLIC)
        .exclude(owner=request.user)
        .prefetch_related('skill_tags')
    )
    total = len(vacancies)
    job_id = str(uuid.uuid4())
    _start_job(job_id, _run_vacancies_job, resume, vacancies, total)

    return render(request, 'matching/computing.html', {
        'subject':    resume.title,
        'total':      total,
        'job_id':     job_id,
        'mode':       'vacancy',
        'cancel_url': reverse('match_cancel_job', args=[job_id]),
        'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=vacancy',
        'done_url':   request.path + f'?job_id={job_id}',
    })


# ── Resumes for vacancy ────────────────────────────────────────────────────────

@login_required
def match_resumes_for_vacancy_view(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, owner=request.user)
    job_id = request.GET.get('job_id', '')

    if job_id:
        job = _get_job(job_id)
        if job.get('done'):
            results = job.get('partial', [])
            _pop_job(job_id)
            return render(request, 'matching/resumes_for_vacancy.html', {
                'vacancy': vacancy,
                'results': results,
                'error':   job.get('error', ''),
            })
        return render(request, 'matching/computing.html', {
            'subject':    vacancy.title,
            'total':      job.get('total', 0),
            'job_id':     job_id,
            'mode':       'resume',
            'cancel_url': reverse('match_cancel_job', args=[job_id]),
            'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=resume',
            'done_url':   request.path + f'?job_id={job_id}',
        })

    resumes = list(
        Resume.objects
        .filter(
            visibility=Resume.Visibility.PUBLIC,
            search_status__in=[Resume.SearchStatus.LOOKING, Resume.SearchStatus.OPEN_TO_OFFERS],
        )
        .exclude(owner=request.user)
        .prefetch_related('skill_tags')
    )
    total = len(resumes)
    job_id = str(uuid.uuid4())
    _start_job(job_id, _run_resumes_job, vacancy, resumes, total)

    return render(request, 'matching/computing.html', {
        'subject':    vacancy.title,
        'total':      total,
        'job_id':     job_id,
        'mode':       'resume',
        'cancel_url': reverse('match_cancel_job', args=[job_id]),
        'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=resume',
        'done_url':   request.path + f'?job_id={job_id}',
    })


# ── JSON API (unchanged) ───────────────────────────────────────────────────────

@login_required
def match_vacancies_for_resume_api(request, pk):
    resume = get_object_or_404(Resume, pk=pk, owner=request.user)
    vacancies = Vacancy.objects.filter(
        visibility=Vacancy.Visibility.PUBLIC
    ).exclude(owner=request.user)
    results = rank_vacancies_for_resume(resume, vacancies)
    return JsonResponse({
        'resume_id': resume.id,
        'resume_title': resume.title,
        'results': [
            {
                'vacancy_id': item['vacancy'].id,
                'title': item['vacancy'].title,
                'company': item['vacancy'].company,
                'score_percent': item['score_percent'],
                'matched_skills': item['matched_skills'],
                'missing_skills': item['missing_skills'],
                'explanation': item['explanation'],
            }
            for item in results
        ],
    })


def _trudvsem_filter(items, salary_min, salary_max, exp_max, schedules):
    """Apply client-side filters to raw Труд Всем vacancy dicts."""
    out = []
    for item in items:
        sal_min_v = item.get('salary_min')
        sal_max_v = item.get('salary_max')
        req = item.get('requirement') or {}
        exp = float(req.get('experience') or 0)
        schedule_raw = (item.get('schedule') or '').lower()
        employment_raw = (item.get('employment') or '').lower()

        if salary_min and not (
            (sal_min_v and int(sal_min_v) >= salary_min) or
            (sal_max_v and int(sal_max_v) >= salary_min)
        ):
            continue
        if salary_max and sal_min_v and int(sal_min_v) > salary_max:
            continue
        if exp_max is not None and exp > exp_max:
            continue
        if schedules:
            is_remote = 'удалённ' in schedule_raw or 'удаленн' in schedule_raw
            is_parttime = 'частичн' in employment_raw or 'гибкий' in schedule_raw
            is_internship = 'стажировк' in employment_raw
            is_fulltime = 'полная' in employment_raw
            match = (
                ('remote' in schedules and is_remote) or
                ('part_time' in schedules and is_parttime) or
                ('internship' in schedules and is_internship) or
                ('full_time' in schedules and is_fulltime) or
                ('full_time' in schedules and not (is_remote or is_parttime or is_internship))
            )
            if not match:
                continue
        out.append(item)
    return out


@login_required
def match_trudvsem_view(request, pk):
    from django.core.cache import cache
    from vacancies.trudvsem_import import TRUDVSEM_REGIONS, _vac_uid, live_search

    resume = get_object_or_404(Resume, pk=pk, owner=request.user)
    job_id = request.GET.get('job_id', '')

    if job_id:
        job = _get_job(job_id)
        if not job:
            messages.error(request, 'Задача не найдена или истекла.')
            return redirect(request.path)
        if job.get('done'):
            results = job.get('partial', [])
            _pop_job(job_id)
            return render(request, 'matching/live_vacancies_for_resume.html', {
                'resume': resume,
                'results': results,
                'error': job.get('error', ''),
            })
        return render(request, 'matching/computing.html', {
            'subject':    resume.title,
            'total':      job.get('total', 0),
            'job_id':     job_id,
            'mode':       'live',
            'cancel_url': reverse('match_cancel_job', args=[job_id]),
            'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=live',
            'done_url':   request.path + f'?job_id={job_id}',
        })

    def _form_ctx(post=None):
        return {
            'resume': resume,
            'regions': TRUDVSEM_REGIONS,
            'post': post or {},
        }

    if request.method == 'POST':
        post = request.POST
        query = post.get('query', '').strip()
        region_code = post.get('region_code', '') or None
        try:
            count = max(5, min(100, int(post.get('count') or 20)))
        except ValueError:
            count = 20

        try:
            salary_min = int(post.get('salary_min') or 0) or None
            salary_max = int(post.get('salary_max') or 0) or None
        except ValueError:
            salary_min = salary_max = None

        try:
            exp_max_raw = post.get('exp_max', '')
            exp_max = float(exp_max_raw) if exp_max_raw else None
        except ValueError:
            exp_max = None

        schedules = post.getlist('schedule')

        # Fetch from API — request more to account for client-side filtering
        fetch_count = min(count * 2, 100)
        try:
            per_page = min(fetch_count, 25)
            items, _ = live_search(query, region_code, offset=0, per_page=per_page)
            if fetch_count > 25:
                more, _ = live_search(query, region_code, offset=25, per_page=min(fetch_count - 25, 25))
                items = items + more
            if fetch_count > 50:
                more2, _ = live_search(query, region_code, offset=50, per_page=min(fetch_count - 50, 25))
                items = items + more2
            if fetch_count > 75:
                more3, _ = live_search(query, region_code, offset=75, per_page=min(fetch_count - 75, 25))
                items = items + more3
        except Exception as e:
            messages.error(request, f'Ошибка при получении вакансий с Труд Всем: {e}')
            return render(request, 'matching/trudvsem_match.html', _form_ctx(post))

        # Apply client-side filters
        if salary_min or salary_max or exp_max is not None or schedules:
            items = _trudvsem_filter(items, salary_min, salary_max, exp_max, schedules)

        # Deduplicate and cap
        seen_uids: set = set()
        vac_items = []
        for raw in items:
            uid = _vac_uid(raw)
            if uid and uid not in seen_uids:
                seen_uids.add(uid)
                cache.set(f'trudvsem_vac_{uid}', raw, 3600)
                vac_items.append((uid, raw))
                if len(vac_items) >= count:
                    break

        if not vac_items:
            messages.warning(request, 'Вакансии по заданным параметрам не найдены. Попробуйте расширить фильтры.')
            return render(request, 'matching/trudvsem_match.html', _form_ctx(post))

        job_id = str(uuid.uuid4())
        _start_job(job_id, _run_live_vacancies_job, resume.pk, vac_items, len(vac_items))
        return redirect(request.path + f'?job_id={job_id}')

    return render(request, 'matching/trudvsem_match.html', _form_ctx())


@login_required
def match_resumes_for_vacancy_api(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, owner=request.user)
    resumes = Resume.objects.filter(
        visibility=Resume.Visibility.PUBLIC,
        search_status__in=[Resume.SearchStatus.LOOKING, Resume.SearchStatus.OPEN_TO_OFFERS],
    ).exclude(owner=request.user)
    results = rank_resumes_for_vacancy(vacancy, resumes)
    return JsonResponse({
        'vacancy_id': vacancy.id,
        'vacancy_title': vacancy.title,
        'results': [
            {
                'resume_id': item['resume'].id,
                'title': item['resume'].title,
                'full_name': item['resume'].full_name,
                'desired_position': item['resume'].desired_position,
                'score_percent': item['score_percent'],
                'matched_skills': item['matched_skills'],
                'missing_skills': item['missing_skills'],
                'explanation': item['explanation'],
            }
            for item in results
        ],
    })
