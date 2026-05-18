import threading
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import applicant_required
from accounts.models import Profile
from resumes.models import Resume
from vacancies.models import FavoriteVacancy, Vacancy
from .services import calculate_match, calculate_match_live, rank_resumes_for_vacancy

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


def _serialize_mixed_result(item):
    if item.get('source') == 'db' or 'vacancy' in item:
        base = _serialize_vacancy_result(item)
        base['source'] = 'db'
        base['detail_url'] = f"/vacancies/{item['vacancy'].pk}/"
        return base
    base = _serialize_live_result(item)
    base['source'] = 'live'
    return base


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
    mode = request.GET.get('mode', 'resume')
    if mode == 'favorites':
        serializer = _serialize_mixed_result
    else:
        serializer = _serialize_resume_result

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


def _run_favorites_job(job_id, resume_pk, db_vacancy_pks, live_items):
    from django.db import connection
    partial = []
    try:
        resume = Resume.objects.prefetch_related('skill_tags').get(pk=resume_pk)
        db_vacancies = list(
            Vacancy.objects.filter(pk__in=db_vacancy_pks).prefetch_related('skill_tags')
        )
        for vacancy in db_vacancies:
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('cancel'):
                    break
            match_data = calculate_match(resume, vacancy)
            match_data['vacancy'] = vacancy
            match_data['source'] = 'db'
            partial.append(match_data)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]['partial'] = sorted(partial, key=lambda x: x['score'], reverse=True)

        from vacancies.trudvsem_import import format_live_item
        for uid, vac_dict in live_items:
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('cancel'):
                    break
            match_data = calculate_match_live(resume, vac_dict)
            match_data['vac_id'] = uid
            match_data['vac_dict'] = vac_dict
            fmt = format_live_item(vac_dict)
            match_data.update({k: fmt[k] for k in ('title', 'company', 'city', 'salary_from', 'salary_to', 'source_url')})
            match_data['source'] = 'live'
            partial.append(match_data)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]['partial'] = sorted(partial, key=lambda x: x['score'], reverse=True)

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


@login_required
@applicant_required
def match_favorites_view(request, pk):
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
            return render(request, 'matching/favorites_results.html', {
                'resume': resume,
                'results': results,
                'error': job.get('error', ''),
            })
        return render(request, 'matching/computing.html', {
            'subject':    resume.title,
            'total':      job.get('total', 0),
            'job_id':     job_id,
            'mode':       'favorites',
            'cancel_url': reverse('match_cancel_job', args=[job_id]),
            'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=favorites',
            'done_url':   request.path + f'?job_id={job_id}',
        })

    favorites = FavoriteVacancy.objects.filter(user=request.user).select_related('vacancy')
    db_vacancy_pks = [f.vacancy_id for f in favorites if f.vacancy_id]
    live_items = [(f.trudvsem_uid, f.trudvsem_data) for f in favorites if f.trudvsem_uid and f.trudvsem_data]
    total = len(db_vacancy_pks) + len(live_items)

    if total == 0:
        messages.warning(request, 'В избранном нет вакансий. Добавьте их на странице вакансии.')
        return redirect('matching_dashboard')

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {'done': False, 'cancel': False, 'error': '', 'partial': [], 'total': total}
    import threading
    threading.Thread(
        target=_run_favorites_job,
        args=(job_id, resume.pk, db_vacancy_pks, live_items),
        daemon=True,
    ).start()

    return render(request, 'matching/computing.html', {
        'subject':    resume.title,
        'total':      total,
        'job_id':     job_id,
        'mode':       'favorites',
        'cancel_url': reverse('match_cancel_job', args=[job_id]),
        'poll_url':   reverse('match_poll_job', args=[job_id]) + '?mode=favorites',
        'done_url':   request.path + f'?job_id={job_id}',
    })


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
