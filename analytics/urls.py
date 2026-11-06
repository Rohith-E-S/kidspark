from django.urls import path

from analytics import views

app_name = 'analytics'

urlpatterns = [
    path('reports/', views.all_reports, name='all_reports'),
    path('report/<int:session_id>/', views.report_detail, name='report_detail'),
]
