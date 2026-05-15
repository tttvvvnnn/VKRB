import json
import time
import urllib.error
import urllib.parse
import urllib.request

from django.utils.html import strip_tags

HH_API = 'https://api.hh.ru'
HEADERS = {
    'User-Agent': 'TalentMatch/1.0 (educational project)',
}

SCHEDULE_TO_TYPE = {
    'fullDay':    'full_time',
    'shift':      'full_time',
    'flexible':   'part_time',
    'remote':     'remote',
    'flyInFlyOut': 'full_time',
}

EXPERIENCE_TO_YEARS = {
    'noExperience': 0,
    'between1And3': 1,
    'between3And6': 3,
    'moreThan6':    6,
}

HH_AREAS = [
    ('', 'Вся Россия'),
    ('1', 'Москва'),
    ('2', 'Санкт-Петербург'),
    ('3', 'Екатеринбург'),
    ('4', 'Новосибирск'),
    ('54', 'Нижний Новгород'),
    ('72', 'Тюмень'),
    ('78', 'Казань'),
    ('88', 'Ростов-на-Дону'),
    ('1202', 'Красноярск'),
]


def _api_get(path, params=None):
    url = HH_API + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None and v != ''}
        url += '?' + urllib.parse.urlencode(clean)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def search_hh(query, area=None, count=10):
    params = {'text': query, 'per_page': min(count, 20)}
    if area:
        params['area'] = area
    return _api_get('/vacancies', params).get('items', [])


def fetch_detail(hh_id):
    return _api_get(f'/vacancies/{hh_id}')


def import_from_hh(query, area, count, owner):
    from resumes.models import Skill
    from .models import Vacancy

    items = search_hh(query, area, count)
    imported, skipped, errors = [], [], []

    for item in items:
        title   = (item.get('name') or '').strip()
        company = ((item.get('employer') or {}).get('name') or '').strip()

        if Vacancy.objects.filter(title=title, company=company, owner=owner).exists():
            skipped.append({'title': title, 'company': company, 'reason': 'уже импортирована'})
            continue

        try:
            detail = fetch_detail(item['id'])
            time.sleep(0.25)
        except Exception as e:
            errors.append({'title': title, 'reason': str(e)})
            continue

        salary      = item.get('salary') or {}
        schedule_id = ((item.get('schedule') or {}).get('id') or 'fullDay')
        exp_id      = ((item.get('experience') or {}).get('id') or 'noExperience')
        snippet     = item.get('snippet') or {}

        description  = strip_tags(detail.get('description') or '').strip() or 'Описание не указано'
        requirements = strip_tags(snippet.get('requirement') or '').strip()
        conditions   = strip_tags(snippet.get('responsibility') or '').strip()

        vacancy = Vacancy.objects.create(
            owner=owner,
            title=title,
            company=company,
            city=((item.get('area') or {}).get('name') or ''),
            employment_type=SCHEDULE_TO_TYPE.get(schedule_id, 'full_time'),
            required_experience_years=EXPERIENCE_TO_YEARS.get(exp_id, 0),
            salary_from=salary.get('from'),
            salary_to=salary.get('to'),
            description=description,
            requirements=requirements,
            conditions=conditions,
            visibility=Vacancy.Visibility.PUBLIC,
        )

        raw_skill_names = [
            (s.get('name') or '').strip()
            for s in (detail.get('key_skills') or [])
            if (s.get('name') or '').strip()
        ]
        if raw_skill_names:
            from matching.services import resolve_skills_to_db
            resolved = resolve_skills_to_db(raw_skill_names, threshold=0.60)
            for skill_name in (resolved or raw_skill_names):
                skill = Skill.objects.filter(name__iexact=skill_name).first()
                if not skill:
                    skill = Skill.objects.create(name=skill_name)
                vacancy.skill_tags.add(skill)

        imported.append(vacancy)

    return imported, skipped, errors