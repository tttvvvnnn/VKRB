from django.conf import settings
from django.db import models
from django.db.models import Q

from resumes.models import Resume, Skill


class Vacancy(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Видно всем'
        HIDDEN = 'hidden', 'Скрыто'

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Полная занятость'
        PART_TIME = 'part_time', 'Частичная занятость'
        PROJECT = 'project', 'Проектная работа'
        INTERNSHIP = 'internship', 'Стажировка'
        REMOTE = 'remote', 'Удалённая работа'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vacancies',
        verbose_name='Владелец'
    )

    title = models.CharField(
        max_length=150,
        verbose_name='Название вакансии'
    )

    company = models.CharField(
        max_length=150,
        verbose_name='Компания'
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Город'
    )

    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        verbose_name='Тип занятости'
    )

    required_experience_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        verbose_name='Требуемый опыт, лет'
    )

    salary_from = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Зарплата от'
    )

    salary_to = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Зарплата до'
    )

    skill_tags = models.ManyToManyField(
        Skill,
        blank=True,
        related_name='vacancies',
        verbose_name='Требуемые навыки'
    )

    description = models.TextField(
        verbose_name='Описание вакансии'
    )

    requirements = models.TextField(
        blank=True,
        verbose_name='Требования к кандидату'
    )

    conditions = models.TextField(
        blank=True,
        verbose_name='Условия работы'
    )

    source_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Ссылка на источник'
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
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.company}'


class VacancyApplication(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        VIEWED = 'viewed', 'Просмотрен'
        ACCEPTED = 'accepted', 'Принят'
        REJECTED = 'rejected', 'Отклонён'

    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Вакансия'
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Резюме'
    )

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vacancy_applications',
        verbose_name='Соискатель'
    )

    cover_letter = models.TextField(
        blank=True,
        verbose_name='Сопроводительное сообщение'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус отклика'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отклика'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Отклик на вакансию'
        verbose_name_plural = 'Отклики на вакансии'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['vacancy', 'resume', 'applicant'],
                name='unique_application_for_vacancy_resume_applicant'
            )
        ]

    def __str__(self):
        return f'{self.resume.title} → {self.vacancy.title}'


class FavoriteVacancy(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_vacancies',
    )
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='favorited_by',
    )
    trudvsem_uid = models.CharField(max_length=255, blank=True)
    trudvsem_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'vacancy'],
                condition=Q(vacancy__isnull=False),
                name='unique_user_vacancy_favorite',
            ),
            models.UniqueConstraint(
                fields=['user', 'trudvsem_uid'],
                condition=~Q(trudvsem_uid=''),
                name='unique_user_trudvsem_favorite',
            ),
        ]

    def __str__(self):
        if self.vacancy:
            return f'★ {self.user} → {self.vacancy.title}'
        return f'★ {self.user} → Trudvsem:{self.trudvsem_uid}'