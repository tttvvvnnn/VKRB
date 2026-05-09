from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0002_skill_resume_skill_tags'),
        ('vacancies', '0002_vacancyapplication'),
    ]

    operations = [
        migrations.AddField(
            model_name='vacancy',
            name='skill_tags',
            field=models.ManyToManyField(
                blank=True,
                related_name='vacancies',
                to='resumes.skill',
                verbose_name='Требуемые навыки',
            ),
        ),
    ]