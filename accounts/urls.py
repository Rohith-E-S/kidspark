from django.urls import path

from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.KidSparkLoginView.as_view(), name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('demo-login/', views.demo_login, name='demo_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('children/add/', views.child_create, name='child_create'),
    path('children/<int:child_id>/edit/', views.child_edit, name='child_edit'),
    path('children/<int:child_id>/delete/', views.child_delete, name='child_delete'),
    path('children/<int:child_id>/leave-classroom/', views.leave_classroom, name='leave_classroom'),
    path('classrooms/join/', views.join_classroom, name='join_classroom'),
]
