from django.conf import settings
from django.db import models


class Skill(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Навык'
    )

    class Meta:
        verbose_name = 'Навык'
        verbose_name_plural = 'Навыки'
        ordering = ['name']

    def __str__(self):
        return self.name


class Resume(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Видно всем'
        HIDDEN = 'hidden', 'Скрыто'

    class SearchStatus(models.TextChoices):
        LOOKING = 'looking', 'Ищет работу'
        NOT_LOOKING = 'not_looking', 'Не находится в поиске'
        OPEN_TO_OFFERS = 'open_to_offers', 'Рассматривает предложения'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resumes',
        verbose_name='Владелец'
    )

    title = models.CharField(
        max_length=150,
        verbose_name='Название резюме',
        help_text='Например: Python-разработчик'
    )

    full_name = models.CharField(
        max_length=150,
        verbose_name='ФИО кандидата'
    )

    desired_position = models.CharField(
        max_length=150,
        verbose_name='Желаемая должность'
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Город'
    )

    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Телефон'
    )

    experience_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        verbose_name='Опыт работы, лет'
    )

    education = models.TextField(
        blank=True,
        verbose_name='Образование'
    )

    skill_tags = models.ManyToManyField(
        Skill,
        blank=True,
        related_name='resumes',
        verbose_name='Навыки'
    )

    work_experience = models.TextField(
        blank=True,
        verbose_name='Описание опыта работы'
    )

    about = models.TextField(
        blank=True,
        verbose_name='Дополнительная информация'
    )

    search_status = models.CharField(
        max_length=30,
        choices=SearchStatus.choices,
        default=SearchStatus.LOOKING,
        verbose_name='Статус поиска'
    )

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        verbose_name='Видимость'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Резюме'
        verbose_name_plural = 'Резюме'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.full_name}'