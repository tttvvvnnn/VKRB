from django.db import models

from resumes.models import Resume
from vacancies.models import Vacancy


class MatchResult(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name='match_results',
        verbose_name='Резюме'
    )
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name='match_results',
        verbose_name='Вакансия'
    )
    score = models.FloatField(verbose_name='Итоговый балл')
    score_percent = models.FloatField(verbose_name='Процент совпадения')
    skill_score_percent = models.FloatField(verbose_name='Балл по навыкам')
    text_score_percent = models.FloatField(verbose_name='Балл по тексту')
    experience_score_percent = models.FloatField(verbose_name='Балл по опыту')
    city_score_percent = models.FloatField(verbose_name='Балл по городу')
    matched_skills = models.JSONField(default=list, verbose_name='Совпавшие навыки')
    missing_skills = models.JSONField(default=list, verbose_name='Недостающие навыки')
    explanation = models.TextField(verbose_name='Объяснение')
    calculated_at = models.DateTimeField(auto_now=True, verbose_name='Дата расчёта')

    class Meta:
        verbose_name = 'Результат сопоставления'
        verbose_name_plural = 'Результаты сопоставления'
        unique_together = [('resume', 'vacancy')]