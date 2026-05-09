from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0003_migrate_resume_skills'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resume',
            name='skills',
        ),
    ]