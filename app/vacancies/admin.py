from django.contrib import admin

from .models import Vacancy, VacancyApplication


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'company',
        'city',
        'employment_type',
        'required_experience_years',
        'visibility',
        'owner',
        'created_at',
    )

    list_filter = (
        'employment_type',
        'visibility',
        'city',
        'created_at',
    )

    search_fields = (
        'title',
        'company',
        'description',
        'requirements',
    )

    filter_horizontal = ('skill_tags',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(VacancyApplication)
class VacancyApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'vacancy',
        'resume',
        'applicant',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'vacancy__title',
        'resume__title',
        'applicant__email',
        'applicant__username',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )