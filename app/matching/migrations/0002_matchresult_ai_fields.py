from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matching', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='matchresult',
            name='ai_score',
            field=models.FloatField(blank=True, null=True, verbose_name='Балл Groq AI'),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='ai_explanation',
            field=models.TextField(blank=True, default='', verbose_name='Пояснение Groq AI'),
        ),
        migrations.AddField(
            model_name='matchresult',
            name='ai_used',
            field=models.BooleanField(default=False, verbose_name='Использован Groq AI'),
        ),
    ]