from django.contrib import admin

from .models import Resume, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


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
        'work_experience',
    )

    filter_horizontal = ('skill_tags',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )