import re

from django.db import migrations


def migrate_skills_forward(apps, schema_editor):
    Skill = apps.get_model('resumes', 'Skill')
    Resume = apps.get_model('resumes', 'Resume')

    for resume in Resume.objects.all():
        raw = resume.skills or ''
        names = [s.strip().lower() for s in re.split(r'[,;\n]+', raw) if s.strip()]
        for name in names:
            skill, _ = Skill.objects.get_or_create(name=name)
            resume.skill_tags.add(skill)


def migrate_skills_backward(apps, schema_editor):
    Resume = apps.get_model('resumes', 'Resume')
    for resume in Resume.objects.all():
        skills_text = ', '.join(s.name for s in resume.skill_tags.all())
        resume.skills = skills_text
        resume.save(update_fields=['skills'])


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0002_skill_resume_skill_tags'),
    ]

    operations = [
        migrations.RunPython(migrate_skills_forward, migrate_skills_backward),
    ]