import json
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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


def calculate_ai_score(resume, vacancy):
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    if not api_key:
        return None, ''

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

Ответь только валидным JSON:
{{"score": <число 0-100>, "explanation": "<одно предложение на русском — почему такая оценка>"}}"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
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
        return None, ''

    data = json.loads(match.group())
    score = max(0.0, min(100.0, float(data['score']))) / 100.0
    explanation = data.get('explanation', '')
    return score, explanation


def _compute_match(resume, vacancy):
    skill_data = calculate_skill_score(resume, vacancy)
    experience_score = calculate_experience_score(resume, vacancy)
    city_score = calculate_city_score(resume, vacancy)

    ai_score, ai_explanation = None, ''
    try:
        ai_score, ai_explanation = calculate_ai_score(resume, vacancy)
    except Exception as e:
        print(f'[Groq AI] Ошибка при вызове API: {e}', flush=True)

    if ai_score is not None:
        final_score = (
            skill_data['score'] * 0.35 +
            ai_score * 0.35 +
            experience_score * 0.20 +
            city_score * 0.10
        )
        explanation = ai_explanation
        text_score_percent = round(ai_score * 100, 2)
        ai_used = True
    else:
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
    }


def calculate_match(resume, vacancy):
    from matching.models import MatchResult

    try:
        cached = MatchResult.objects.get(resume=resume, vacancy=vacancy)
        if cached.calculated_at >= resume.updated_at and cached.calculated_at >= vacancy.updated_at:
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
        }
    )

    return result


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