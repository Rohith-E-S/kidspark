from django.urls import path

from assessments import views

app_name = 'assessments'

urlpatterns = [
    path('select/', views.select_test, name='select_test'),
    path('start/<int:child_id>/', views.start_test, name='start_test'),
    path('session/<int:session_id>/', views.quiz_play, name='session'),
]
