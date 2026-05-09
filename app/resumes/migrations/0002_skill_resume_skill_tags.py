from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Навык')),
            ],
            options={
                'verbose_name': 'Навык',
                'verbose_name_plural': 'Навыки',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='resume',
            name='skill_tags',
            field=models.ManyToManyField(
                blank=True,
                related_name='resumes',
                to='resumes.skill',
                verbose_name='Навыки',
            ),
        ),
    ]