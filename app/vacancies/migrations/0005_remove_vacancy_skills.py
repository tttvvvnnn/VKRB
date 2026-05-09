from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vacancies', '0004_migrate_vacancy_skills'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vacancy',
            name='skills',
        ),
    ]