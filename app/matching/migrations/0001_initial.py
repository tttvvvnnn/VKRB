import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('resumes', '0004_remove_resume_skills'),
        ('vacancies', '0005_remove_vacancy_skills'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(verbose_name='Итоговый балл')),
                ('score_percent', models.FloatField(verbose_name='Процент совпадения')),
                ('skill_score_percent', models.FloatField(verbose_name='Балл по навыкам')),
                ('text_score_percent', models.FloatField(verbose_name='Балл по тексту')),
                ('experience_score_percent', models.FloatField(verbose_name='Балл по опыту')),
                ('city_score_percent', models.FloatField(verbose_name='Балл по городу')),
                ('matched_skills', models.JSONField(default=list, verbose_name='Совпавшие навыки')),
                ('missing_skills', models.JSONField(default=list, verbose_name='Недостающие навыки')),
                ('explanation', models.TextField(verbose_name='Объяснение')),
                ('calculated_at', models.DateTimeField(auto_now=True, verbose_name='Дата расчёта')),
                ('resume', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='match_results',
                    to='resumes.resume',
                    verbose_name='Резюме',
                )),
                ('vacancy', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='match_results',
                    to='vacancies.vacancy',
                    verbose_name='Вакансия',
                )),
            ],
            options={
                'verbose_name': 'Результат сопоставления',
                'verbose_name_plural': 'Результаты сопоставления',
                'unique_together': {('resume', 'vacancy')},
            },
        ),
    ]