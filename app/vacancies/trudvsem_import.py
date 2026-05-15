import hashlib
import json
import re
import ssl
import time
import urllib.parse
import urllib.request

TRUDVSEM_API = 'https://opendata.trudvsem.ru/api/v1'
HEADERS = {'User-Agent': 'TalentMatch/1.0 (educational project)'}

# Маппинг популярных городов → код региона trudvsem
CITY_TO_REGION = {
    'москва':            '77',
    'санкт-петербург':   '78',
    'питер':             '78',
    'спб':               '78',
    'екатеринбург':      '66',
    'новосибирск':       '54',
    'нижний новгород':   '52',
    'нижний':            '52',
    'тюмень':            '72',
    'казань':            '16',
    'ростов':            '61',
    'красноярск':        '24',
    'челябинск':         '74',
    'уфа':               '02',
    'воронеж':           '36',
    'самара':            '63',
    'омск':              '55',
    'краснодар':         '23',
    'пермь':             '59',
    'волгоград':         '34',
}

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

_SKILL_PREFIXES = (
    'навык работы с ',
    'знание ',
    'владение ',
    'умение работать с ',
    'опыт работы с ',
)


def _vac_uid(item):
    """Stable unique ID for a vacancy based on its URL (vac_url is unique per vacancy)."""
    import logging
    log = logging.getLogger(__name__)

    url = (item.get('vac_url') or '').strip()
    if url:
        return hashlib.sha1(url.encode()).hexdigest()[:20]

    # vac_url missing — log so we can see which vacancies are affected
    title = (item.get('job-name') or '').strip()
    company_id = str((item.get('company') or {}).get('id') or '')
    internal_id = str(item.get('id') or '')
    uid = hashlib.sha1(f'{company_id}_{internal_id}'.encode()).hexdigest()[:20]
    log.warning('TRUDVSEM _vac_uid | NO vac_url | title=%r | company_id=%r | internal_id=%r | uid=%s',
                title, company_id, internal_id, uid)
    return uid


def _api_get(path, params=None):
    url = TRUDVSEM_API + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None and v != ''}
        url += '?' + urllib.parse.urlencode(clean)
    req = urllib.request.Request(url, headers=HEADERS)

    # trudvsem.ru often drops SSL connections; retry with a permissive context on failure
    for attempt in range(2):
        try:
            if attempt == 0:
                ctx = ssl.create_default_context()
            else:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            if attempt == 1:
                raise
            err = str(exc)
            if 'SSL' in err or 'EOF' in err or 'certificate' in err.lower():
                continue
            raise


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


def city_to_region_code(city_text):
    """Try to map a city name to a trudvsem region code."""
    if not city_text:
        return None
    return CITY_TO_REGION.get(city_text.strip().lower())


def live_search(query, region_code=None, offset=0, per_page=12):
    """Live search for vacancy list page. Returns (items, total)."""
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


def format_live_item(item):
    """Convert raw trudvsem API dict to a clean dict for template rendering."""
    region = item.get('region') or {}
    city = (region.get('name') or '').replace('Город ', '').replace('г. ', '').strip()
    requirement = item.get('requirement') or {}
    salary_min = item.get('salary_min')
    salary_max = item.get('salary_max')
    skills_raw = list(set(item.get('skills') or []))
    skills = [_clean_skill(s) for s in skills_raw if s]
    skills = [s for s in skills if s][:8]
    return {
        'id':          _vac_uid(item),
        'title':       (item.get('job-name') or '').strip(),
        'company':     ((item.get('company') or {}).get('name') or '').strip(),
        'city':        city,
        'salary_from': int(salary_min) if salary_min else None,
        'salary_to':   int(salary_max) if salary_max else None,
        'employment':  (item.get('employment') or '').strip(),
        'experience':  requirement.get('experience', 0),
        'source_url':  (item.get('vac_url') or '').strip(),
        'description': (item.get('duty') or '')[:300].strip(),
        'skills':      skills,
    }


def fetch_vacancy(vac_id):
    """Fetch a single vacancy by its Trudvsem internal id."""
    try:
        data = _api_get(f'/vacancies/vacancy/{vac_id}')
        item = (data.get('results') or {}).get('vacancy')
        if item:
            return item
    except Exception:
        pass
    return {}


def format_vacancy_detail(item):
    """Convert raw trudvsem API dict to a full dict for the detail page."""
    region = item.get('region') or {}
    city = (region.get('name') or '').replace('Город ', '').replace('г. ', '').strip()
    requirement = item.get('requirement') or {}
    salary_min = item.get('salary_min')
    salary_max = item.get('salary_max')
    skills_raw = list(set(item.get('skills') or []))
    skills = [_clean_skill(s) for s in skills_raw if s]
    skills = [s for s in skills if s]
    contact = item.get('contact') or {}
    return {
        'id':           _vac_uid(item),
        'title':        (item.get('job-name') or '').strip(),
        'company':      ((item.get('company') or {}).get('name') or '').strip(),
        'city':         city,
        'salary_from':  int(salary_min) if salary_min else None,
        'salary_to':    int(salary_max) if salary_max else None,
        'employment':   (item.get('employment') or '').strip(),
        'schedule':     (item.get('schedule') or '').strip(),
        'experience':   requirement.get('experience', 0),
        'source_url':   (item.get('vac_url') or '').strip(),
        'description':  (item.get('duty') or '').strip(),
        'requirements': (item.get('requirements') or '').strip(),
        'conditions':   (item.get('benefit') or '').strip(),
        'skills':       skills,
        'contact_name': (contact.get('full-name') or contact.get('name') or '').strip(),
        'contact_phone': (contact.get('phones') or contact.get('phone') or '').strip(),
        'contact_email': (contact.get('email') or '').strip(),
    }


def _clean_skill(raw):
    name = raw.strip()
    name_lower = name.lower()

    for prefix in _SKILL_PREFIXES:
        if name_lower.startswith(prefix):
            name = name[len(prefix):]
            break

    # "Python / Питон" → "Python"
    if ' / ' in name:
        name = name.split(' / ')[0]

    # "PostgreSQL (Postgres)" → "PostgreSQL"
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)

    return name.strip(' /').strip()


# ── Vacancy text structure parsing ────────────────────────────────────────────

# Known Russian HR section headers → section type (lowercase keys)
_SECTION_MAP: dict[str, str] = {
    # duties
    'обязанности': 'duty', 'задачи': 'duty', 'функционал': 'duty',
    'функции': 'duty', 'что предстоит делать': 'duty', 'что нужно делать': 'duty',
    'ваши задачи': 'duty', 'основные задачи': 'duty', 'задачи и функции': 'duty',
    'задачи которые предстоит решать': 'duty',
    # requirements
    'требования': 'requirements', 'что нужно': 'requirements',
    'необходимо': 'requirements', 'от кандидата': 'requirements',
    'пожелания': 'requirements', 'ожидания': 'requirements',
    'требования к кандидату': 'requirements', 'профиль кандидата': 'requirements',
    'ваши навыки': 'requirements', 'мы ожидаем': 'requirements',
    'для нас важно': 'requirements', 'мы от вас ожидаем': 'requirements',
    'что мы ожидаем': 'requirements', 'пожелания к кандидату': 'requirements',
    'будет плюсом': 'requirements', 'будет преимуществом': 'requirements',
    # conditions
    'условия': 'conditions', 'мы предлагаем': 'conditions',
    'что предлагаем': 'conditions', 'предлагаем': 'conditions',
    'мы гарантируем': 'conditions', 'предоставляем': 'conditions',
    'условия работы': 'conditions', 'что мы предлагаем': 'conditions',
}

# Pattern 1 — headers on their own line (e.g. "Требования:" or "ТРЕБОВАНИЯ")
_LINE_HEADER_RE = re.compile(
    r'(?im)^[ \t]*(' + '|'.join(re.escape(k) for k in _SECTION_MAP) + r')[ \t]*:?[ \t]*$'
)

# Pattern 2 — headers inline in semicolon/newline-separated text
# Matches "HEADER:" or "; HEADER:" or ". HEADER:" anywhere in text
_INLINE_HEADER_RE = re.compile(
    r'(?:^|[;.\n])[ \t]*(' + '|'.join(re.escape(k) for k in _SECTION_MAP) + r')[ \t]*:',
    re.IGNORECASE,
)


def parse_vacancy_sections(text):
    """
    Split Russian vacancy text into {duty, requirements, conditions} sections.
    Handles both line-based headers and inline (semicolon-separated) formats.
    Returns a dict with keys that were found; empty dict if no structure detected.
    """
    if not text:
        return {}

    # Try line-based approach first
    matches = list(_LINE_HEADER_RE.finditer(text))
    if not matches:
        # Fall back to inline approach
        matches = list(_INLINE_HEADER_RE.finditer(text))

    if not matches:
        return {}

    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1).strip().lower()
        sec = _SECTION_MAP.get(key)
        if not sec:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip().strip(';').strip()
        if content:
            sections[sec] = (sections.get(sec, '') + '\n' + content).strip()

    return sections


def enrich_vac_dict(vac_dict):
    """
    Return a copy of a raw Труд Всем dict with better-structured fields.
    Tries to split the `duty` blob into duty/requirements/conditions sections.
    When no structure is detected, copies duty text into requirements so the
    matching AI always has context to work with.
    """
    enriched = dict(vac_dict)
    duty = (vac_dict.get('duty') or '').strip()
    has_reqs = bool((vac_dict.get('requirements') or '').strip())

    if not duty:
        return enriched

    sections = parse_vacancy_sections(duty)

    if sections:
        if 'duty' in sections:
            enriched['duty'] = sections['duty']
        if 'requirements' in sections:
            enriched['requirements'] = (
                ((vac_dict.get('requirements') or '') + '\n' + sections['requirements']).strip()
                if has_reqs else sections['requirements']
            )
        if 'conditions' in sections and not (vac_dict.get('benefit') or '').strip():
            enriched['benefit'] = sections['conditions']
    elif not has_reqs:
        # No section headers found and requirements is empty:
        # put the full duty text in requirements so AI sees the full context.
        enriched['requirements'] = duty

    return enriched


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