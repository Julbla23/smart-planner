from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("home/", views.home, name="home"),

    path("tasks/", views.task_list, name="task_list"),
    path("tasks/add/", views.add_task, name="add_task"),
    path("tasks/backlog/", views.backlog_tasks_list, name="backlog_tasks_list"),
    path("tasks/<int:n>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:n>/done/", views.status_done, name="status_done"),
    path("tasks/<int:n>/delete/", views.delete_task, name="delete_task"),

    path("categories/add/", views.add_category, name="add_category"),

    path("calendar/", views.calendar, name="calendar"),
    path("calendar/<int:year>/<int:month>/", views.calendar, name="calendar_month"),
    path("calendar/<int:year>/<int:month>/<int:day>/", views.tasks_by_day, name="tasks_by_day"),

    path("tasks/statistics/weekly/", views.show_weekly_statistics, name="show_weekly_statistics"),
    path("tasks/statistics/monthly/", views.show_monthly_statistics, name="show_monthly_statistics"),
    path("tasks/statistics/quarterly/", views.show_quarterly_statistics, name="show_quarterly_statistics"),

    path("ai/", views.ai_kroki, name="ai_kroki"),
]