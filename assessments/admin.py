from django.contrib import admin

from assessments.models import (
    AssessmentSession,
    Category,
    Choice,
    Question,
    SessionResponse,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ('text', 'icon_name', 'is_correct', 'score_weight')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'pillar', 'icon_name')
    list_filter = ('pillar',)
    search_fields = ('code', 'name')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'short_text', 'category', 'question_type', 'age_group',
        'difficulty_weight', 'order',
    )
    list_filter = ('category__pillar', 'category', 'question_type', 'age_group')
    search_fields = ('text', 'category__code')
    list_editable = ('difficulty_weight', 'order')
    list_select_related = ('category',)
    inlines = [ChoiceInline]

    @admin.display(description='Question')
    def short_text(self, obj):
        return obj.text[:70]


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = (
        'child', 'started_at', 'completed_at', 'is_completed',
        'current_question_index',
    )
    list_filter = ('is_completed',)
    search_fields = ('child__name',)
    list_select_related = ('child',)


@admin.register(SessionResponse)
class SessionResponseAdmin(admin.ModelAdmin):
    list_display = ('session', 'question', 'selected_choice', 'time_taken_seconds')
    list_select_related = ('session', 'question', 'selected_choice')
    search_fields = ('session__child__name', 'question__text')
