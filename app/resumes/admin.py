from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'full_name',
        'desired_position',
        'city',
        'experience_years',
        'search_status',
        'visibility',
        'owner',
        'created_at',
    )

    list_filter = (
        'search_status',
        'visibility',
        'city',
        'created_at',
    )

    search_fields = (
        'title',
        'full_name',
        'desired_position',
        'skills',
        'work_experience',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )