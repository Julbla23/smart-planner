from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Task, TaskMoveHistory
from .views import chart_buckets, statistics

User = get_user_model()


def at(day, hour=12, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class PlannerTestCase(TestCase):

    def setUp(self):
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)

        self.ala = User.objects.create_user(username="ala", password="TajneHaslo123!")
        self.ola = User.objects.create_user(username="ola", password="TajneHaslo123!")
        self.client.force_login(self.ala)

    def make_task(self, user=None, name="Zadanie", day=None, hour=12, **extra):
        return Task.objects.create(
            user=user or self.ala,
            name=name,
            planned_date=at(day or self.today, hour),
            duration_minutes=extra.pop("duration_minutes", 30),
            **extra,
        )



class AuthTests(TestCase):

    def test_pages_require_login(self):
        for name in ["home", "task_list", "add_task", "calendar",
                     "show_weekly_statistics", "backlog_tasks_list", "ai_kroki"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertRedirects(response, f"{reverse('login')}?next={reverse(name)}")

    def test_register_creates_user(self):
        response = self.client.post(reverse("register"), {
            "username": "nowa",
            "password1": "BardzoTrudne123!",
            "password2": "BardzoTrudne123!",
        })
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.filter(username="nowa").exists())

    def test_register_rejects_different_passwords(self):
        self.client.post(reverse("register"), {
            "username": "nowa",
            "password1": "BardzoTrudne123!",
            "password2": "InneHaslo123!",
        })
        self.assertFalse(User.objects.filter(username="nowa").exists())



class DataIsolationTests(PlannerTestCase):

    def test_task_list_shows_only_own_tasks(self):
        self.make_task(name="Zadanie Ali")
        self.make_task(user=self.ola, name="Zadanie Oli")

        response = self.client.get(reverse("task_list"))

        self.assertContains(response, "Zadanie Ali")
        self.assertNotContains(response, "Zadanie Oli")

    def test_cannot_edit_someone_elses_task(self):
        task = self.make_task(user=self.ola)
        response = self.client.get(reverse("edit_task", args=[task.id]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_someone_elses_task(self):
        task = self.make_task(user=self.ola)
        response = self.client.post(reverse("delete_task", args=[task.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(id=task.id).exists())

    def test_cannot_mark_someone_elses_task_as_done(self):
        task = self.make_task(user=self.ola)
        response = self.client.post(reverse("status_done", args=[task.id]))
        self.assertEqual(response.status_code, 404)
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")

    def test_task_form_shows_only_own_categories(self):
        Category.objects.create(name="Moja kategoria", color="#f4c2c2", user=self.ala)
        Category.objects.create(name="Cudza kategoria", color="#f4c2c2", user=self.ola)

        response = self.client.get(reverse("add_task"))

        self.assertContains(response, "Moja kategoria")
        self.assertNotContains(response, "Cudza kategoria")



class TaskActionTests(PlannerTestCase):

    def task_data(self, **changes):
        data = {
            "title": "Nowe zadanie",
            "planned_date": f"{self.tomorrow:%Y-%m-%d} 10:00",
            "deadline": "",
            "duration_minutes": 30,
            "priority": "medium",
            "category": "",
        }
        data.update(changes)
        return data

    def test_add_task(self):
        response = self.client.post(reverse("add_task"), self.task_data())

        self.assertRedirects(response, reverse("task_list"))
        task = Task.objects.get(name="Nowe zadanie")
        self.assertEqual(task.user, self.ala)
        self.assertEqual(task.status, "todo")
        self.assertEqual(task.priority, "medium")

    def test_add_task_warns_about_overlap_and_does_not_save(self):
        self.make_task(name="Istniejące", day=self.tomorrow, hour=10, duration_minutes=60)

        response = self.client.post(
            reverse("add_task"),
            self.task_data(planned_date=f"{self.tomorrow:%Y-%m-%d} 10:30"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konflikt terminów")
        self.assertFalse(Task.objects.filter(name="Nowe zadanie").exists())

    def test_add_task_right_after_another_is_not_an_overlap(self):
        self.make_task(name="Istniejące", day=self.tomorrow, hour=10, duration_minutes=60)

        self.client.post(
            reverse("add_task"),
            self.task_data(planned_date=f"{self.tomorrow:%Y-%m-%d} 11:00"),
        )

        self.assertTrue(Task.objects.filter(name="Nowe zadanie").exists())

    def test_cannot_use_someone_elses_category(self):
        foreign = Category.objects.create(name="Cudza", color="#f4c2c2", user=self.ola)

        self.client.post(reverse("add_task"), self.task_data(category=foreign.id))

        self.assertFalse(Task.objects.filter(name="Nowe zadanie").exists())

    def test_moving_task_saves_history_and_keeps_status(self):
        task = self.make_task(day=self.today, hour=9)

        self.client.post(reverse("edit_task", args=[task.id]), {
            "name": task.name,
            "planned_date": f"{self.tomorrow:%Y-%m-%d} 09:00",
            "deadline": "",
            "duration_minutes": 30,
            "priority": "low",
            "status": "todo",
            "category": "",
        })

        task.refresh_from_db()
        self.assertEqual(task.planned_date.date(), self.tomorrow)
        self.assertEqual(task.status, "todo")
        self.assertEqual(TaskMoveHistory.objects.filter(task=task).count(), 1)

    def test_changing_status_in_edit_sets_status_changed_at(self):
        task = self.make_task()

        self.client.post(reverse("edit_task", args=[task.id]), {
            "name": task.name,
            "planned_date": f"{self.today:%Y-%m-%d} 12:00",
            "deadline": "",
            "duration_minutes": 30,
            "priority": "low",
            "status": "done",
            "category": "",
        })

        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.status_changed_at)

    def test_mark_task_as_done(self):
        task = self.make_task()

        self.client.post(reverse("status_done", args=[task.id]))

        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.status_changed_at)

    def test_delete_task(self):
        task = self.make_task()
        self.client.post(reverse("delete_task", args=[task.id]))
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_delete_and_done_do_not_work_with_get(self):
        task = self.make_task()

        self.assertEqual(self.client.get(reverse("delete_task", args=[task.id])).status_code, 405)
        self.assertEqual(self.client.get(reverse("status_done", args=[task.id])).status_code, 405)
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")



class CategoryTests(PlannerTestCase):

    def test_add_category_belongs_to_user(self):
        self.client.post(reverse("add_category"), {"name": "Sport", "color": "#7fb3e8"})

        category = Category.objects.get(name="Sport")
        self.assertEqual(category.user, self.ala)
        self.assertEqual(category.color, "#7fb3e8")

    def test_invalid_color_is_replaced_with_default(self):
        self.client.post(reverse("add_category"), {"name": "Sport", "color": "red; background: url(x)"})
        self.assertEqual(Category.objects.get(name="Sport").color, "#f4c2c2")

    def test_empty_name_is_ignored(self):
        self.client.post(reverse("add_category"), {"name": "   ", "color": "#7fb3e8"})
        self.assertEqual(Category.objects.count(), 0)



class CompletionTests(PlannerTestCase):

    def test_zero_percent_when_no_tasks(self):
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.context["percentage"], 0)

    def test_percentage_is_rounded_whole_number(self):
        self.make_task(status="done")
        self.make_task()
        self.make_task()

        response = self.client.get(reverse("task_list"))

        self.assertEqual(response.context["percentage"], 33)



class StatisticsTests(PlannerTestCase):

    def week(self):
        start = self.today - timedelta(days=self.today.weekday())
        return start, start + timedelta(days=6)

    def test_overdue_includes_past_tasks_from_any_period(self):
        old = self.make_task(name="Stare", day=self.today - timedelta(days=60))
        start, end = self.week()

        stats = statistics(self.ala, start, end)

        self.assertIn(old, stats["overdue_tasks"])

    def test_task_with_passed_deadline_is_overdue_not_todo(self):
        task = self.make_task(day=self.today, deadline=self.yesterday)
        start, end = self.week()

        stats = statistics(self.ala, start, end)

        self.assertIn(task, stats["overdue_tasks"])
        self.assertNotIn(task, stats["todo_tasks"])

    def test_todays_task_is_todo_not_overdue(self):
        task = self.make_task(day=self.today)
        start, end = self.week()

        stats = statistics(self.ala, start, end)

        self.assertIn(task, stats["todo_tasks"])
        self.assertNotIn(task, stats["overdue_tasks"])

    def test_done_is_counted_by_completion_date(self):
        task = self.make_task(day=self.today - timedelta(days=60), status="done",
                              status_changed_at=timezone.now())
        start, end = self.week()

        stats = statistics(self.ala, start, end)

        self.assertIn(task, stats["done_tasks"])

    def test_statistics_pages_open(self):
        self.make_task()
        for name in ["show_weekly_statistics", "show_monthly_statistics", "show_quarterly_statistics"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class ChartBucketsTests(TestCase):

    def test_week_has_seven_days(self):
        buckets = chart_buckets("week", date(2026, 11, 16), date(2026, 11, 22))
        self.assertEqual(len(buckets), 7)
        self.assertEqual(buckets[0][2], "Pn 16.11")
        self.assertEqual(buckets[-1][2], "Nd 22.11")

    def test_month_is_split_into_weeks_without_gaps(self):
        start, end = date(2026, 11, 1), date(2026, 11, 30)

        buckets = chart_buckets("month", start, end)

        self.assertEqual(buckets[0][:2], (date(2026, 11, 1), date(2026, 11, 1)))
        self.assertEqual(buckets[-1][1], end)
        for (_, prev_end, _), (next_start, _, _) in zip(buckets, buckets[1:]):
            self.assertEqual(next_start, prev_end + timedelta(days=1))



class CalendarTests(PlannerTestCase):

    def test_calendar_counts_tasks_per_day(self):
        self.make_task(hour=9)
        self.make_task(hour=14)
        self.make_task(user=self.ola)  # cudze zadanie nie może się liczyć

        response = self.client.get(reverse("calendar"))

        cells = [cell for week in response.context["calendar_data"] for cell in week]
        today_cell = next(cell for cell in cells if cell["day"] == self.today.day)
        self.assertEqual(today_cell["count"], 2)
        self.assertTrue(today_cell["is_today"])

    def test_invalid_month_returns_404(self):
        response = self.client.get(reverse("calendar_month", args=[2026, 13]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_day_returns_404(self):
        response = self.client.get(reverse("tasks_by_day", args=[2026, 2, 31]))
        self.assertEqual(response.status_code, 404)

    def test_january_previous_month_is_december_of_previous_year(self):
        response = self.client.get(reverse("calendar_month", args=[2026, 1]))
        self.assertEqual(response.context["prev_year"], 2025)
        self.assertEqual(response.context["prev_month"], 12)



class HomeTests(PlannerTestCase):

    def test_home_counts(self):
        self.make_task(status="done", status_changed_at=timezone.now())
        self.make_task()
        self.make_task(day=self.yesterday)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["done_count"], 1)
        self.assertEqual(response.context["todo_count"], 1)
        self.assertEqual(response.context["overdue_count"], 1)



class AiStepsTests(PlannerTestCase):

    @patch("planner.views.rozbij_cel_na_kroki", return_value=["Krok 1", "Krok 2"])
    def test_propose_shows_steps_from_ai(self, mock_ai):
        response = self.client.post(reverse("ai_kroki"), {"akcja": "zaproponuj", "goal": "Nauczyć się Django"})

        mock_ai.assert_called_once_with("Nauczyć się Django")
        self.assertContains(response, "Krok 1")
        self.assertContains(response, "Krok 2")

    def test_add_selected_steps(self):
        self.client.post(reverse("ai_kroki"), {
            "akcja": "dodaj",
            "kroki": ["Krok 1", "Krok 2"],
            "data": f"{self.tomorrow:%Y-%m-%d}",
        })

        self.assertEqual(Task.objects.filter(user=self.ala).count(), 2)

    def test_add_without_date_does_not_crash(self):
        response = self.client.post(reverse("ai_kroki"), {"akcja": "dodaj", "kroki": ["Krok 1"], "data": ""})

        self.assertRedirects(response, reverse("ai_kroki"))
        self.assertEqual(Task.objects.count(), 0)