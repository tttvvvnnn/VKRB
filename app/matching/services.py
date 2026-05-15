import json
import os
import re
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


_skill_cache: dict = {'names': None, 'ts': 0.0}
_SKILL_CACHE_TTL = 300  # seconds


def _get_db_skill_names():
    now = time.time()
    if _skill_cache['names'] is None or now - _skill_cache['ts'] > _SKILL_CACHE_TTL:
        from resumes.models import Skill
        _skill_cache['names'] = list(Skill.objects.values_list('name', flat=True))
        _skill_cache['ts'] = now
    return _skill_cache['names']


def extract_skills_from_text(text):
    """Find DB skill names mentioned in free text via word-boundary search."""
    if not text:
        return []
    db_names = _get_db_skill_names()
    if not db_names:
        return []
    text_lower = text.lower()
    found, seen_lower = [], set()
    for name in db_names:
        nl = name.lower()
        if nl in seen_lower or len(name) < 2:
            continue
        pattern = r'(?<![a-zA-Zа-яА-Я0-9])' + re.escape(nl) + r'(?![a-zA-Zа-яА-Я0-9])'
        if re.search(pattern, text_lower):
            seen_lower.add(nl)
            found.append(name)
    return found


def resolve_skills_to_db(raw_names, threshold=0.52):
    """Map raw skill strings to closest DB Skill names using char n-gram TF-IDF.

    Returns a list of DB skill names (original case) for matched skills.
    Unmatched skills are dropped — caller decides whether to keep or discard them.
    """
    if not raw_names:
        return []
    db_names = _get_db_skill_names()
    if not db_names:
        return list(raw_names)
    try:
        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        vectorizer.fit(list(db_names) + list(raw_names))
        db_matrix = vectorizer.transform(db_names)
        raw_matrix = vectorizer.transform(raw_names)
        sims = cosine_similarity(raw_matrix, db_matrix)
        resolved, seen_lower = [], set()
        for row in sims:
            best_idx = int(row.argmax())
            if row[best_idx] >= threshold:
                name = db_names[best_idx]
                if name.lower() not in seen_lower:
                    seen_lower.add(name.lower())
                    resolved.append(name)
        return resolved
    except Exception:
        return list(raw_names)


def normalize_text(value):
    if not value:
        return ''
    return str(value).lower().strip()


def get_skill_names(obj):
    return {s.name.lower() for s in obj.skill_tags.all()}


def build_resume_text(resume):
    skills_text = ' '.join(s.name for s in resume.skill_tags.all())
    return ' '.join([
        normalize_text(resume.title),
        normalize_text(resume.desired_position),
        normalize_text(skills_text),
        normalize_text(resume.education),
        normalize_text(resume.work_experience),
        normalize_text(resume.about),
    ])


def build_vacancy_text(vacancy):
    skills_text = ' '.join(s.name for s in vacancy.skill_tags.all())
    return ' '.join([
        normalize_text(vacancy.title),
        normalize_text(skills_text),
        normalize_text(vacancy.description),
        normalize_text(vacancy.requirements),
        normalize_text(vacancy.conditions),
    ])


def calculate_text_similarity(resume, vacancy):
    resume_text = build_resume_text(resume)
    vacancy_text = build_vacancy_text(vacancy)

    if not resume_text or not vacancy_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform([resume_text, vacancy_text])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except ValueError:
        return 0.0


def calculate_skill_score(resume, vacancy):
    resume_skills = get_skill_names(resume)
    vacancy_skills = get_skill_names(vacancy)

    if not vacancy_skills:
        return {'score': 0.0, 'matched_skills': [], 'missing_skills': []}

    matched_skills = sorted(resume_skills.intersection(vacancy_skills))
    missing_skills = sorted(vacancy_skills.difference(resume_skills))

    return {
        'score': len(matched_skills) / len(vacancy_skills),
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
    }


def calculate_experience_score(resume, vacancy):
    resume_exp = float(resume.experience_years or 0)
    required_exp = float(vacancy.required_experience_years or 0)

    if required_exp <= 0:
        return 1.0
    if resume_exp >= required_exp:
        return 1.0
    return resume_exp / required_exp


def calculate_city_score(resume, vacancy):
    resume_city = normalize_text(resume.city)
    vacancy_city = normalize_text(vacancy.city)

    if not resume_city or not vacancy_city:
        return 0.5
    return 1.0 if resume_city == vacancy_city else 0.0


def _groq_chat(client, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            msg = str(e)
            if '429' in msg:
                wait = 5.0
                m = re.search(r'try again in ([\d.]+)s', msg)
                if m:
                    wait = float(m.group(1)) + 0.5
                time.sleep(wait)
                continue
            raise
    return client.chat.completions.create(**kwargs)


def calculate_ai_score(resume, vacancy):
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    if not api_key:
        return None, '', None

    from groq import Groq

    skills_resume = ', '.join(s.name for s in resume.skill_tags.all()) or 'не указаны'
    skills_vacancy = ', '.join(s.name for s in vacancy.skill_tags.all()) or 'не указаны'

    user_prompt = f"""Оцени соответствие кандидата вакансии от 0 до 100.

РЕЗЮМЕ:
Желаемая должность: {resume.desired_position}
Навыки: {skills_resume}
Опыт работы: {(resume.work_experience or 'не указан')[:600]}
О себе: {(resume.about or 'не указано')[:300]}

ВАКАНСИЯ:
Название: {vacancy.title}
Требуемые навыки: {skills_vacancy}
Требования: {(vacancy.requirements or 'не указаны')[:600]}
Описание: {vacancy.description[:600]}

Также определи, сколько лет РЕЛЕВАНТНОГО опыта (непосредственно по профилю данной вакансии) есть у кандидата.
Опыт в несвязанных сферах (например, год работы электриком при вакансии разработчика) не считается релевантным.

Ответь только валидным JSON:
{{"score": <число 0-100>, "relevant_experience_years": <число лет релевантного опыта, float>, "explanation": "<одно предложение на русском — почему такая оценка>"}}"""

    groq_kwargs = {'api_key': api_key}
    groq_base_url = os.environ.get('GROQ_BASE_URL', '').strip()
    if groq_base_url:
        groq_kwargs['base_url'] = groq_base_url

    client = Groq(**groq_kwargs)
    response = _groq_chat(
        client,
        model='llama-3.3-70b-versatile',
        messages=[
            {
                'role': 'system',
                'content': (
                    'Ты эксперт по подбору персонала. '
                    'Отвечай только валидным JSON без markdown и пояснений.'
                ),
            },
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=256,
        temperature=0.1,
    )

    text = response.choices[0].message.content.strip()
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if not match:
        return None, '', None

    data = json.loads(match.group())
    score = max(0.0, min(100.0, float(data['score']))) / 100.0
    relevant_exp = max(0.0, float(data.get('relevant_experience_years', 0)))
    explanation = data.get('explanation', '')
    return score, explanation, relevant_exp


def calculate_ai_score_for_live(resume, vac_dict):
    """
    AI scoring for live Труд Всем vacancies.
    Uses llama-3.1-8b-instant (500k tokens/day free tier) instead of 70b.
    Same Groq call returns score + skills — no extra API calls.
    """
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    if not api_key:
        return None, '', None, []

    from groq import Groq
    from vacancies.trudvsem_import import _clean_skill, enrich_vac_dict

    d = enrich_vac_dict(vac_dict)
    title = (d.get('job-name') or '').strip()
    duty = (d.get('duty') or '').strip()
    requirements = (d.get('requirements') or '').strip()
    benefit = (d.get('benefit') or '').strip()
    raw_skills = d.get('skills') or []
    api_skills = ', '.join(
        {_clean_skill(s) for s in raw_skills if s and _clean_skill(s)}
    ) or ''
    req = d.get('requirement') or {}

    # Build vacancy context — pass full text split across sections
    vac_lines = [f"Должность: {title}"]
    if api_skills:
        vac_lines.append(f"Навыки (из API): {api_skills}")
    exp_api = float(req.get('experience') or 0)
    if exp_api:
        vac_lines.append(f"Требуемый опыт: {exp_api} лет")
    if duty and requirements and duty != requirements:
        vac_lines.append(f"Обязанности:\n{duty[:400]}")
        vac_lines.append(f"Требования:\n{requirements[:500]}")
    elif requirements:
        vac_lines.append(f"Текст вакансии:\n{requirements[:800]}")
    elif duty:
        vac_lines.append(f"Текст вакансии:\n{duty[:800]}")

    vac_text = '\n\n'.join(vac_lines)

    skills_resume = ', '.join(s.name for s in resume.skill_tags.all()) or 'не указаны'

    user_prompt = f"""Оцени соответствие кандидата вакансии (0-100). Текст вакансии может быть неструктурированным — извлеки требования самостоятельно.

РЕЗЮМЕ: {resume.desired_position} | навыки: {skills_resume} | опыт: {(resume.work_experience or '')[:400]}

ВАКАНСИЯ:
{vac_text}

JSON: {{"score":<0-100>,"relevant_experience_years":<float>,"explanation":"<1 предложение рус>","required_skills":["навык1",...]}}"""

    groq_kwargs = {'api_key': api_key}
    groq_base_url = os.environ.get('GROQ_BASE_URL', '').strip()
    if groq_base_url:
        groq_kwargs['base_url'] = groq_base_url

    client = Groq(**groq_kwargs)
    response = _groq_chat(
        client,
        model='llama-3.1-8b-instant',
        messages=[
            {
                'role': 'system',
                'content': 'HR-эксперт. Анализируй вакансии и резюме. Отвечай только валидным JSON.',
            },
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=250,
        temperature=0.1,
    )

    text = response.choices[0].message.content.strip()
    # Extract the outermost JSON object (may contain nested arrays)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None, '', None, []

    data = json.loads(match.group())
    score = max(0.0, min(100.0, float(data['score']))) / 100.0
    relevant_exp = max(0.0, float(data.get('relevant_experience_years', 0)))
    explanation = data.get('explanation', '')
    raw_skills = data.get('required_skills') or []
    ai_skills = [s.strip() for s in raw_skills if isinstance(s, str) and s.strip()]
    return score, explanation, relevant_exp, ai_skills


def _compute_match(resume, vacancy):
    skill_data = calculate_skill_score(resume, vacancy)
    city_score = calculate_city_score(resume, vacancy)

    ai_score, ai_explanation, relevant_exp_years = None, '', None
    try:
        ai_score, ai_explanation, relevant_exp_years = calculate_ai_score(resume, vacancy)
    except Exception as e:
        print(f'[Groq AI] Ошибка при вызове API: {e}', flush=True)

    if ai_score is not None:
        required_exp = float(vacancy.required_experience_years or 0)
        if required_exp <= 0:
            experience_score = 1.0
        else:
            experience_score = min(1.0, relevant_exp_years / required_exp)

        final_score = (
            skill_data['score'] * 0.35 +
            ai_score * 0.35 +
            experience_score * 0.20 +
            city_score * 0.10
        )
        explanation = ai_explanation
        text_score_percent = round(ai_score * 100, 2)
        ai_used = True
        breakdown = _build_breakdown(
            skill_score=skill_data['score'],
            second_score=ai_score,
            second_label='AI-оценка',
            experience_score=experience_score,
            city_score=city_score,
            weights=(35, 35, 20, 10),
            experience_note=_experience_note(relevant_exp_years, required_exp),
        )
    else:
        experience_score = calculate_experience_score(resume, vacancy)
        text_score = calculate_text_similarity(resume, vacancy)
        final_score = (
            skill_data['score'] * 0.40 +
            text_score * 0.35 +
            experience_score * 0.20 +
            city_score * 0.05
        )
        explanation = build_explanation(
            score_percent=round(final_score * 100, 2),
            skill_data=skill_data,
            text_score=text_score,
            experience_score=experience_score,
            city_score=city_score,
        )
        text_score_percent = round(text_score * 100, 2)
        ai_used = False
        required_exp = float(vacancy.required_experience_years or 0)
        breakdown = _build_breakdown(
            skill_score=skill_data['score'],
            second_score=text_score,
            second_label='Текстовое сходство',
            experience_score=experience_score,
            city_score=city_score,
            weights=(40, 35, 20, 5),
        )

    score_percent = round(final_score * 100, 2)

    return {
        'score': final_score,
        'score_percent': score_percent,
        'skill_score_percent': round(skill_data['score'] * 100, 2),
        'text_score_percent': text_score_percent,
        'experience_score_percent': round(experience_score * 100, 2),
        'city_score_percent': round(city_score * 100, 2),
        'matched_skills': skill_data['matched_skills'],
        'missing_skills': skill_data['missing_skills'],
        'explanation': explanation,
        'progress_percent': max(0, min(100, round(score_percent))),
        'ai_used': ai_used,
        'ai_score': ai_score,
        'relevant_experience_years': relevant_exp_years,
        'breakdown': breakdown,
    }


def calculate_match(resume, vacancy):
    from matching.models import MatchResult

    try:
        cached = MatchResult.objects.get(resume=resume, vacancy=vacancy)
        if cached.calculated_at >= resume.updated_at and cached.calculated_at >= vacancy.updated_at:
            required_exp = float(vacancy.required_experience_years or 0)
            if cached.ai_used:
                exp_note = _experience_note(cached.relevant_experience_years, required_exp)
                breakdown = _build_breakdown(
                    skill_score=cached.skill_score_percent / 100,
                    second_score=cached.text_score_percent / 100,
                    second_label='AI-оценка',
                    experience_score=cached.experience_score_percent / 100,
                    city_score=cached.city_score_percent / 100,
                    weights=(35, 35, 20, 10),
                    experience_note=exp_note,
                )
            else:
                breakdown = _build_breakdown(
                    skill_score=cached.skill_score_percent / 100,
                    second_score=cached.text_score_percent / 100,
                    second_label='Текстовое сходство',
                    experience_score=cached.experience_score_percent / 100,
                    city_score=cached.city_score_percent / 100,
                    weights=(40, 35, 20, 5),
                )
            return {
                'score': cached.score,
                'score_percent': cached.score_percent,
                'skill_score_percent': cached.skill_score_percent,
                'text_score_percent': cached.text_score_percent,
                'experience_score_percent': cached.experience_score_percent,
                'city_score_percent': cached.city_score_percent,
                'matched_skills': cached.matched_skills,
                'missing_skills': cached.missing_skills,
                'explanation': cached.explanation,
                'progress_percent': max(0, min(100, round(cached.score_percent))),
                'ai_used': cached.ai_used,
                'ai_score': cached.ai_score,
                'relevant_experience_years': cached.relevant_experience_years,
                'breakdown': breakdown,
            }
    except MatchResult.DoesNotExist:
        pass

    result = _compute_match(resume, vacancy)

    MatchResult.objects.update_or_create(
        resume=resume,
        vacancy=vacancy,
        defaults={
            'score': result['score'],
            'score_percent': result['score_percent'],
            'skill_score_percent': result['skill_score_percent'],
            'text_score_percent': result['text_score_percent'],
            'experience_score_percent': result['experience_score_percent'],
            'city_score_percent': result['city_score_percent'],
            'matched_skills': result['matched_skills'],
            'missing_skills': result['missing_skills'],
            'explanation': result['explanation'],
            'ai_score': result['ai_score'],
            'ai_used': result['ai_used'],
            'ai_explanation': result['explanation'] if result['ai_used'] else '',
            'relevant_experience_years': result['relevant_experience_years'],
        }
    )

    return result


def _experience_note(relevant_years, required_years):
    if relevant_years is None:
        return ''
    if required_years <= 0:
        return f'{relevant_years:.1f} лет (требований нет)'
    return f'{relevant_years:.1f} из {required_years:.0f} лет релевантного опыта'


def _build_breakdown(skill_score, second_score, second_label, experience_score, city_score, weights, experience_note=''):
    w_skill, w_second, w_exp, w_city = weights
    return [
        {
            'label': 'Навыки',
            'score_percent': round(skill_score * 100, 1),
            'weight': w_skill,
            'contribution': round(skill_score * w_skill, 1),
            'note': '',
        },
        {
            'label': second_label,
            'score_percent': round(second_score * 100, 1),
            'weight': w_second,
            'contribution': round(second_score * w_second, 1),
            'note': '',
        },
        {
            'label': 'Опыт',
            'score_percent': round(experience_score * 100, 1),
            'weight': w_exp,
            'contribution': round(experience_score * w_exp, 1),
            'note': experience_note,
        },
        {
            'label': 'Город',
            'score_percent': round(city_score * 100, 1),
            'weight': w_city,
            'contribution': round(city_score * w_city, 1),
            'note': '',
        },
    ]


def build_explanation(score_percent, skill_data, text_score, experience_score, city_score):
    parts = []

    if score_percent >= 75:
        parts.append('Высокая релевантность.')
    elif score_percent >= 50:
        parts.append('Средняя релевантность.')
    else:
        parts.append('Низкая релевантность.')

    if skill_data['matched_skills']:
        parts.append('Совпавшие навыки: ' + ', '.join(skill_data['matched_skills']) + '.')
    if skill_data['missing_skills']:
        parts.append('Недостающие навыки: ' + ', '.join(skill_data['missing_skills']) + '.')

    if text_score >= 0.5:
        parts.append('Текст резюме хорошо соответствует описанию вакансии.')
    elif text_score >= 0.25:
        parts.append('Текстовое сходство умеренное.')
    else:
        parts.append('Текстовое сходство низкое.')

    if experience_score >= 1:
        parts.append('Опыт кандидата соответствует требованию.')
    else:
        parts.append('Опыт кандидата ниже требуемого.')

    if city_score == 1:
        parts.append('Город совпадает.')
    elif city_score == 0.5:
        parts.append('Город не указан у одной из сторон.')
    else:
        parts.append('Город не совпадает.')

    return ' '.join(parts)


def rank_vacancies_for_resume(resume, vacancies):
    results = []
    for vacancy in vacancies:
        match_data = calculate_match(resume, vacancy)
        match_data['vacancy'] = vacancy
        results.append(match_data)
    return sorted(results, key=lambda x: x['score'], reverse=True)


def rank_resumes_for_vacancy(vacancy, resumes):
    results = []
    for resume in resumes:
        match_data = calculate_match(resume, vacancy)
        match_data['resume'] = resume
        results.append(match_data)
    return sorted(results, key=lambda x: x['score'], reverse=True)


# ── Live (Труд Всем) matching — no DB storage ──────────────────────────────────

class _SkillProxy:
    def __init__(self, name):
        self.name = name


class _SkillSetProxy:
    def __init__(self, names):
        self._items = [_SkillProxy(n) for n in names]

    def all(self):
        return self._items


class _VacancyProxy:
    """Duck-type Vacancy for matching functions, backed by a raw Труд Всем dict."""

    def __init__(self, vac_dict):
        from vacancies.trudvsem_import import _clean_skill, enrich_vac_dict
        d = enrich_vac_dict(vac_dict)

        region = d.get('region') or {}
        requirement = d.get('requirement') or {}

        self.title = (d.get('job-name') or '').strip()
        self.company = ((d.get('company') or {}).get('name') or '').strip()
        self.city = (region.get('name') or '').replace('Город ', '').replace('г. ', '').strip()
        self.description = (d.get('duty') or '').strip()
        self.requirements = (d.get('requirements') or '').strip()
        self.conditions = (d.get('benefit') or '').strip()
        try:
            self.required_experience_years = float(requirement.get('experience') or 0)
        except (TypeError, ValueError):
            self.required_experience_years = 0.0

        raw_skills = d.get('skills') or []
        seen, names = set(), []
        for s in raw_skills:
            cleaned = _clean_skill(s)
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                names.append(cleaned)

        # Map API skills to DB skills via TF-IDF
        resolved = resolve_skills_to_db(names) if names else []

        # Extract skills mentioned in vacancy text
        vacancy_text = ' '.join(filter(None, [self.title, self.description, self.requirements]))
        text_skills = extract_skills_from_text(vacancy_text)

        # Merge: DB-resolved API skills + text-extracted skills
        merged, merged_lower = [], {s.lower() for s in resolved}
        merged.extend(resolved)
        for s in text_skills:
            if s.lower() not in merged_lower:
                merged_lower.add(s.lower())
                merged.append(s)

        self._seen_lower: set = merged_lower
        self.skill_tags = _SkillSetProxy(merged if merged else names)

    def enrich_skills(self, extra_names: list[str]) -> None:
        """Add skill names returned by the AI into skill_tags (deduplicates)."""
        added = []
        for name in extra_names:
            if name and name.lower() not in self._seen_lower:
                self._seen_lower.add(name.lower())
                added.append(name)
        if added:
            existing = [s.name for s in self.skill_tags.all()]
            self.skill_tags = _SkillSetProxy(existing + added)


def calculate_match_live(resume, vac_dict):
    """Full match (with AI if available) against a live Труд Всем dict. No DB caching."""
    proxy = _VacancyProxy(vac_dict)
    city_score = calculate_city_score(resume, proxy)
    required_exp = float(proxy.required_experience_years)

    # ── AI scoring (also extracts required skills) ──────────────────────────
    ai_score, ai_explanation, relevant_exp_years, ai_skills = None, '', None, []
    try:
        ai_score, ai_explanation, relevant_exp_years, ai_skills = calculate_ai_score_for_live(resume, vac_dict)
    except Exception as e:
        print(f'[Groq AI Live] Error: {e}', flush=True)

    # ── Enrich proxy skills with AI-extracted list ───────────────────────────
    if ai_skills:
        proxy.enrich_skills(ai_skills)

    # ── Skill score (now uses enriched skills) ───────────────────────────────
    skill_data = calculate_skill_score(resume, proxy)

    if ai_score is not None:
        exp_score = 1.0 if required_exp <= 0 else min(1.0, relevant_exp_years / required_exp)
        final_score = (
            skill_data['score'] * 0.35 +
            ai_score * 0.35 +
            exp_score * 0.20 +
            city_score * 0.10
        )
        breakdown = _build_breakdown(
            skill_score=skill_data['score'],
            second_score=ai_score,
            second_label='AI-оценка',
            experience_score=exp_score,
            city_score=city_score,
            weights=(35, 35, 20, 10),
            experience_note=_experience_note(relevant_exp_years, required_exp),
        )
        text_score_percent = round(ai_score * 100, 2)
        ai_used = True
        explanation = ai_explanation
    else:
        exp_score = calculate_experience_score(resume, proxy)
        text_score = calculate_text_similarity(resume, proxy)
        final_score = (
            skill_data['score'] * 0.40 +
            text_score * 0.35 +
            exp_score * 0.20 +
            city_score * 0.05
        )
        explanation = build_explanation(round(final_score * 100, 2), skill_data, text_score, exp_score, city_score)
        text_score_percent = round(text_score * 100, 2)
        ai_used = False
        relevant_exp_years = None
        breakdown = _build_breakdown(
            skill_score=skill_data['score'],
            second_score=text_score,
            second_label='Текстовое сходство',
            experience_score=exp_score,
            city_score=city_score,
            weights=(40, 35, 20, 5),
        )

    score_percent = round(final_score * 100, 2)
    return {
        'score': final_score,
        'score_percent': score_percent,
        'skill_score_percent': round(skill_data['score'] * 100, 2),
        'text_score_percent': text_score_percent,
        'experience_score_percent': round(exp_score * 100, 2),
        'city_score_percent': round(city_score * 100, 2),
        'matched_skills': skill_data['matched_skills'],
        'missing_skills': skill_data['missing_skills'],
        'explanation': explanation,
        'progress_percent': max(0, min(100, round(score_percent))),
        'ai_used': ai_used,
        'ai_score': ai_score,
        'relevant_experience_years': relevant_exp_years,
        'breakdown': breakdown,
    }


def calculate_match_quick(resume, vac_dict):
    """Fast TF-IDF-only match for detail pages (no AI, no DB)."""
    proxy = _VacancyProxy(vac_dict)
    skill_data = calculate_skill_score(resume, proxy)
    city_score = calculate_city_score(resume, proxy)
    experience_score = calculate_experience_score(resume, proxy)
    text_score = calculate_text_similarity(resume, proxy)

    final_score = (
        skill_data['score'] * 0.40 +
        text_score * 0.35 +
        experience_score * 0.20 +
        city_score * 0.05
    )
    score_percent = round(final_score * 100, 2)
    return {
        'score': final_score,
        'score_percent': score_percent,
        'skill_score_percent': round(skill_data['score'] * 100, 2),
        'text_score_percent': round(text_score * 100, 2),
        'experience_score_percent': round(experience_score * 100, 2),
        'city_score_percent': round(city_score * 100, 2),
        'matched_skills': skill_data['matched_skills'],
        'missing_skills': skill_data['missing_skills'],
        'explanation': build_explanation(score_percent, skill_data, text_score, experience_score, city_score),
        'progress_percent': max(0, min(100, round(score_percent))),
        'ai_used': False,
        'ai_score': None,
        'relevant_experience_years': None,
        'breakdown': _build_breakdown(
            skill_score=skill_data['score'],
            second_score=text_score,
            second_label='Текстовое сходство',
            experience_score=experience_score,
            city_score=city_score,
            weights=(40, 35, 20, 5),
        ),
    }