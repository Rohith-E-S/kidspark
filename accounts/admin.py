from django.contrib import admin

from accounts.models import ChildProfile, Classroom


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'academic_year', 'code', 'teacher', 'created_at')
    list_filter = ('grade', 'academic_year')
    search_fields = ('name', 'code', 'teacher__username')
    readonly_fields = ('code', 'created_at')
    list_select_related = ('teacher',)


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'age_group', 'grade', 'classroom', 'parent', 'created_at')
    list_filter = ('age_group', 'classroom', 'avatar_color')
    search_fields = ('name', 'parent__username', 'grade', 'classroom__name')
    readonly_fields = ('age_group', 'created_at')
    list_select_related = ('parent', 'classroom')
