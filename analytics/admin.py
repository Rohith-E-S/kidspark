from django.contrib import admin

from analytics.models import AssessmentResult


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = (
        'session', 'persona_title', 'overall_aptitude_percentage',
        'dominant_aptitude', 'dominant_interest', 'generated_at',
    )
    list_filter = ('dominant_aptitude', 'dominant_interest')
    search_fields = ('session__child__name', 'persona_title')
    readonly_fields = ('generated_at',)
    list_select_related = ('session', 'session__child')
