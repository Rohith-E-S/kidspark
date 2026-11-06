from django.contrib import admin

from accounts.models import ChildProfile


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'age_group', 'grade', 'parent', 'created_at')
    list_filter = ('age_group', 'avatar_color')
    search_fields = ('name', 'parent__username', 'grade')
    readonly_fields = ('age_group', 'created_at')
    list_select_related = ('parent',)
