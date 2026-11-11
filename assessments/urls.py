from django.urls import path

from assessments import teacher_views, views

app_name = 'assessments'

urlpatterns = [
    path('select/', views.select_test, name='select_test'),
    path('start/<int:child_id>/', views.start_test, name='start_test'),
    path('session/<int:session_id>/', views.quiz_play, name='session'),

    # Teacher Portal — Question Bank Management
    path('teacher/', teacher_views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/questions/add/', teacher_views.teacher_question_create, name='teacher_question_create'),
    path('teacher/questions/<int:question_id>/edit/', teacher_views.teacher_question_edit, name='teacher_question_edit'),
    path('teacher/questions/<int:question_id>/delete/', teacher_views.teacher_question_delete, name='teacher_question_delete'),
    path('teacher/questions/<int:question_id>/preview/', teacher_views.teacher_question_preview, name='teacher_question_preview'),

    # Teacher Portal — Classroom & Student Management
    path('teacher/classrooms/', teacher_views.classroom_list, name='classroom_list'),
    path('teacher/classrooms/create/', teacher_views.classroom_create, name='classroom_create'),
    path('teacher/classrooms/<int:classroom_id>/', teacher_views.classroom_detail, name='classroom_detail'),
    path('teacher/classrooms/<int:classroom_id>/edit/', teacher_views.classroom_edit, name='classroom_edit'),
    path('teacher/classrooms/<int:classroom_id>/students/add/', teacher_views.student_add, name='student_add'),
    path('teacher/students/<int:student_id>/edit/', teacher_views.student_edit, name='student_edit'),
    path('teacher/students/<int:student_id>/remove/', teacher_views.student_remove, name='student_remove'),
]
