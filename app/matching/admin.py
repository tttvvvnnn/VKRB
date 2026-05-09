from django.contrib import admin

from .models import MatchResult


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = (
        'resume',
        'vacancy',
        'score_percent',
        'ai_used',
        'calculated_at',
    )
    list_filter = ('ai_used',)
    readonly_fields = (
        'resume', 'vacancy',
        'score', 'score_percent',
        'skill_score_percent', 'text_score_percent',
        'experience_score_percent', 'city_score_percent',
        'matched_skills', 'missing_skills',
        'explanation', 'ai_score', 'ai_explanation', 'ai_used',
        'calculated_at',
    )