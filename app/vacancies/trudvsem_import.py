import json
import time
import urllib.parse
import urllib.request

TRUDVSEM_API = 'https://opendata.trudvsem.ru/api/v1'
HEADERS = {'User-Agent': 'TalentMatch/1.0 (educational project)'}

TRUDVSEM_REGIONS = [
    ('', 'Вся Россия'),
    ('77', 'Москва'),
    ('78', 'Санкт-Петербург'),
    ('66', 'Екатеринбург (Свердловская обл.)'),
    ('54', 'Новосибирск (Новосибирская обл.)'),
    ('52', 'Нижний Новгород (Нижегородская обл.)'),
    ('72', 'Тюмень (Тюменская обл.)'),
    ('16', 'Казань (Татарстан)'),
    ('61', 'Ростов-на-Дону (Ростовская обл.)'),
    ('24', 'Красноярск (Красноярский край)'),
]

# employment и schedule приходят на русском языке
EMPLOYMENT_RU_TO_TYPE = {
    'полная занятость':             'full_time',
    'частичная занятость':          'part_time',
    'проектная работа':             'project',
    'проектная/временная работа':   'project',
    'стажировка':                   'internship',
    'волонтёрство':                 'part_time',
}

SCHEDULE_RU_TO_TYPE = {
    'удалённая работа':  'remote',
    'удаленная работа':  'remote',
    'гибкий':            'part_time',
    'гибкий график':     'part_time',
}

SKILL_PREFIX = 'навык работы с '


def _api_get(path, params=None):
    url = TRUDVSEM_API + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None and v != ''}
        url += '?' + urllib.parse.urlencode(clean)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def search_trudvsem(query, region_code=None, count=10):
    params = {
        'text':   query,
        'limit':  min(count, 100),
        'offset': 0,
    }
    if region_code:
        params['regionCode'] = region_code

    data = _api_get('/vacancies', params)
    vacancies_raw = (data.get('results') or {}).get('vacancies') or []
    return [v['vacancy'] for v in vacancies_raw if isinstance(v, dict) and 'vacancy' in v]


def live_search(query, region_code=None, page=1, per_page=12):
    """Live search for vacancy list page. Returns (items, total)."""
    offset = (page - 1) * per_page
    params = {'limit': per_page, 'offset': offset}
    if query:
        params['text'] = query
    if region_code:
        params['regionCode'] = region_code

    data = _api_get('/vacancies', params)
    total = (data.get('meta') or {}).get('total', 0)
    vacancies_raw = (data.get('results') or {}).get('vacancies') or []
    items = [v['vacancy'] for v in vacancies_raw if isinstance(v, dict) and 'vacancy' in v]
    return items, total


def _clean_skill(raw):
    name = raw.strip()
    if name.lower().startswith(SKILL_PREFIX):
        name = name[len(SKILL_PREFIX):]
    return name.strip(' /').strip()


def _resolve_employment_type(employment, schedule):
    schedule_lower = (schedule or '').lower()
    if schedule_lower in SCHEDULE_RU_TO_TYPE:
        return SCHEDULE_RU_TO_TYPE[schedule_lower]
    return EMPLOYMENT_RU_TO_TYPE.get((employment or '').lower(), 'full_time')


def import_from_trudvsem(query, region_code, count, owner):
    from resumes.models import Skill
    from .models import Vacancy

    items = search_trudvsem(query, region_code, count)
    imported, skipped, errors = [], [], []

    for item in items:
        title   = (item.get('job-name') or '').strip()
        company = ((item.get('company') or {}).get('name') or '').strip()

        if not title:
            continue

        if Vacancy.objects.filter(title=title, company=company, owner=owner).exists():
            skipped.append({'title': title, 'company': company, 'reason': 'уже импортирована'})
            continue

        try:
            requirement = item.get('requirement') or {}
            try:
                experience_years = float(requirement.get('experience') or 0)
            except (TypeError, ValueError):
                experience_years = 0

            employment_type = _resolve_employment_type(
                item.get('employment'), item.get('schedule')
            )

            salary_min = item.get('salary_min')
            salary_max = item.get('salary_max')

            region = item.get('region') or {}
            city = (region.get('name') or '').replace('Город ', '').replace('г. ', '').strip()

            duty         = (item.get('duty') or '').strip() or 'Описание не указано'
            requirements = (item.get('requirements') or '').strip()
            conditions   = (item.get('benefit') or '').strip()
            source_url   = (item.get('vac_url') or '').strip()

            vacancy = Vacancy.objects.create(
                owner=owner,
                title=title,
                company=company,
                city=city,
                employment_type=employment_type,
                required_experience_years=experience_years,
                salary_from=int(salary_min) if salary_min else None,
                salary_to=int(salary_max) if salary_max else None,
                description=duty,
                requirements=requirements,
                conditions=conditions,
                source_url=source_url,
                visibility=Vacancy.Visibility.PUBLIC,
            )

            seen = set()
            for raw_skill in (item.get('skills') or []):
                name = _clean_skill(raw_skill)
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())
                skill = Skill.objects.filter(name__iexact=name).first()
                if not skill:
                    skill = Skill.objects.create(name=name)
                vacancy.skill_tags.add(skill)

            imported.append(vacancy)
            time.sleep(0.1)

        except Exception as e:
            errors.append({'title': title or '(без названия)', 'reason': str(e)})

    return imported, skipped, errors