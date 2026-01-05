from django.urls import path
from . import views

urlpatterns = [
    path('', views.result_print_view, name='print_results'),
    path('graduating/', views.graduating_students_report, name='graduating_students'),
    path('student/<int:student_id>/results/', views.student_result_sheet, name='student_results'),
    path('department/<int:department_id>/results/', views.department_results, name='department_results'),
    path('attendance/', views.attendance_sheet_view, name='attendance_sheet'),  # Add this
]