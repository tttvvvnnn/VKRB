from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    class Role(models.TextChoices):
        APPLICANT = 'applicant', 'Соискатель'
        RECRUITER = 'recruiter', 'Рекрутер'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.APPLICANT,
        verbose_name='Роль пользователя'
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
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'{self.user.email or self.user.username} — {self.get_role_display()}'

    @property
    def is_recruiter(self):
        return self.role == self.Role.RECRUITER


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)