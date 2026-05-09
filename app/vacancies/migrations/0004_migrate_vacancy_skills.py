import re

from django.db import migrations


def migrate_skills_forward(apps, schema_editor):
    Skill = apps.get_model('resumes', 'Skill')
    Vacancy = apps.get_model('vacancies', 'Vacancy')

    for vacancy in Vacancy.objects.all():
        raw = vacancy.skills or ''
        names = [s.strip().lower() for s in re.split(r'[,;\n]+', raw) if s.strip()]
        for name in names:
            skill, _ = Skill.objects.get_or_create(name=name)
            vacancy.skill_tags.add(skill)


def migrate_skills_backward(apps, schema_editor):
    Vacancy = apps.get_model('vacancies', 'Vacancy')
    for vacancy in Vacancy.objects.all():
        skills_text = ', '.join(s.name for s in vacancy.skill_tags.all())
        vacancy.skills = skills_text
        vacancy.save(update_fields=['skills'])


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0003_migrate_resume_skills'),
        ('vacancies', '0003_vacancy_skill_tags'),
    ]

    operations = [
        migrations.RunPython(migrate_skills_forward, migrate_skills_backward),
    ]