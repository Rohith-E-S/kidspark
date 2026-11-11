from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', account_views.dashboard, name='dashboard'),
    path('teacher/', RedirectView.as_view(pattern_name='assessments:teacher_dashboard', permanent=False), name='teacher_shortcut'),
    path('assessments/', include('assessments.urls')),
    path('analytics/', include('analytics.urls')),
]
