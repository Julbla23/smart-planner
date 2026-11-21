import re
from calendar import monthcalendar
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q
from django.db.models.functions import ExtractDay, TruncDate
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date, datetime, time, timedelta
from .ai import rozbij_cel_na_kroki
from .forms import AddTask, EditTask, GoalForm
from .models import Category, Task, TaskMoveHistory

@login_required
def task_list(request):
    today = date.today()
    tasks = Task.objects.filter(planned_date__date=today, user=request.user).order_by("planned_date")
    return render(request, "planner/tasks_list.html", {
        "tasks": tasks,
        "percentage": complete_percentage(request),
        "selected_date": today,
        "is_today": True,
    })

@login_required
def backlog_tasks_list(request):
    backlog_tasks = Task.objects.filter(planned_date__lt = timezone.now(), status="todo", user=request.user)
    return render(request, "planner/backlog_tasks_list.html", {"backlog_tasks": backlog_tasks})

@require_POST
@login_required
def delete_task(request, n):
    task = get_object_or_404(Task, id=n, user=request.user)
    task.delete()
    messages.success(request, f"Usunięto: {task.name}")
    return redirect("task_list")


@require_POST
@login_required
def status_done(request, n):
    task = get_object_or_404(Task, id=n, user=request.user)
    task.status = "done"
    task.status_changed_at = timezone.now()
    task.save()
    messages.success(request, f"Zrobione: {task.name} 🎉")
    return redirect("task_list")


def find_over_lapping_tasks(
        user, planned_date, duration_minutes, excluded_task_id=None
):
    new_start = planned_date
    new_end = planned_date + timedelta(minutes=duration_minutes)

    tasks = Task.objects.filter(user=user)

    if excluded_task_id is not None:
        tasks = tasks.exclude(id=excluded_task_id)

    overlapping_tasks = []

    for task in tasks:
        existing_start = task.planned_date
        existing_end = (
            task.planned_date + timedelta(minutes=task.duration_minutes)
        )

        tasks_overlap = (
            new_start < existing_end
            and new_end > existing_start
        )

        if tasks_overlap:
            overlapping_tasks.append(task)

    return overlapping_tasks

@login_required
def add_task(request):
    if request.method == "POST":
        form = AddTask(request.POST, user=request.user)
        if form.is_valid():
            name = form.cleaned_data['title']
            priority = form.cleaned_data['priority']
            planned_date = form.cleaned_data['planned_date']
            duration_minutes = form.cleaned_data['duration_minutes']
            category= form.cleaned_data['category']
            deadline = form.cleaned_data['deadline']

            overlapping_tasks = find_over_lapping_tasks(
                user=request.user,
                planned_date=planned_date,
                duration_minutes=duration_minutes
            )

            if overlapping_tasks:
                return render(
                    request, "planner/forms.html",
                    {
                        "form" : form,
                        "overlapping_tasks" : overlapping_tasks
                    }
                )
            Task.objects.create(name=name, priority=priority, planned_date=planned_date, duration_minutes=duration_minutes, category=category, deadline=deadline, user=request.user)
            messages.success(request, "Zadanie dodane")
            return redirect("task_list")
    else:
        form = AddTask(user=request.user)
    return render(request, "planner/forms.html", {"form": form})

@login_required
def edit_task(request, n):
    task = get_object_or_404(Task, id=n, user=request.user)
    old_planned_date = task.planned_date
    old_status = task.status

    if request.method == "POST":
        form = EditTask(request.POST, instance=task, user=request.user)
        if form.is_valid():
            new_planned_date = form.cleaned_data["planned_date"]
            new_status = form.cleaned_data["status"]

            # przesunięcie: zapisujemy historię, ale status zostaje bez zmian
            if old_planned_date != new_planned_date:
                TaskMoveHistory.objects.create(
                    task=task,
                    old_planned_date=old_planned_date,
                    new_planned_date=new_planned_date,
                )

            # zmiana statusu: zapamiętujemy kiedy (potrzebne do statystyk)
            if old_status != new_status:
                task.status_changed_at = timezone.now()

            form.save()
            messages.success(request, "Zmiany zapisane")
            return redirect("task_list")
    else:
        form = EditTask(instance=task, user=request.user)

    return render(request, "planner/forms.html", {"form": form, "editing": True})
@login_required
def home(request):
    today = date.today()
    is_overdue = Q(planned_date__date__lt=today) | Q(deadline__lt=today)

    today_tasks = Task.objects.filter(user=request.user, planned_date__date=today)

    context = {
        "todo_count": today_tasks.filter(status="todo").exclude(is_overdue).count(),
        "done_count": today_tasks.filter(status="done").count(),
        "overdue_count": Task.objects.filter(is_overdue, user=request.user, status="todo").count(),
        "next_task": (today_tasks
                      .filter(status="todo", planned_date__gte=timezone.now())
                      .order_by("planned_date")
                      .first()),
        "percentage": complete_percentage(request),
    }
    return render(request, "planner/home.html", context)

MIESIACE = [
    "", "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
]


@login_required
def calendar(request, year=None, month=None):
    today = date.today()
    year = year or today.year
    month = month or today.month

    if not 1 <= month <= 12:
        raise Http404("Nie ma takiego miesiąca")

    # ile zadań jest w każdym dniu miesiąca, np. {3: 2, 18: 6}
    rows = (Task.objects
            .filter(user=request.user, planned_date__year=year, planned_date__month=month)
            .annotate(day=ExtractDay("planned_date"))
            .values("day")
            .annotate(count=Count("id")))
    counts = {row["day"]: row["count"] for row in rows}

    # każdy dzień jako słownik: numer, liczba zadań, czy to dziś
    weeks = []
    for week in monthcalendar(year, month):
        days = []
        for d in week:
            days.append({
                "day": d,
                "count": counts.get(d, 0),
                "is_today": d != 0 and date(year, month, d) == today,
            })
        weeks.append(days)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return render(request, "planner/calendar.html", {
        "calendar_data": weeks,
        "month_name": MIESIACE[month],
        "month": month,
        "year": year,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "is_current_month": year == today.year and month == today.month,
    })

@login_required
def tasks_by_day(request, year, month, day):
    try:
        selected_date = date(year, month, day)
    except ValueError:
        raise Http404("Nie ma takiego dnia")

    tasks = Task.objects.filter(planned_date__date=selected_date, user=request.user).order_by("planned_date")
    return render(request, "planner/tasks_list.html", {
        "tasks": tasks,
        "percentage": complete_percentage(request, selected_date),
        "selected_date": selected_date,
        "is_today": selected_date == date.today(),
    })

@require_POST
@login_required
def add_category(request):
    name = request.POST.get("name", "").strip()
    color = request.POST.get("color", "")

    # przyjmujemy tylko kolor w formacie #rrggbb, np. #f4c2c2
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = "#f4c2c2"

    if name:
        Category.objects.create(name=name, color=color, user=request.user)
        messages.success(request, f"Dodano kategorię: {name}")

    return redirect(request.META.get("HTTP_REFERER") or "add_task")

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rejestracja udana")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'planner/register.html', {'form': form})

def complete_percentage(request, day=None):
    day = day or date.today()
    day_tasks = Task.objects.filter(planned_date__date=day, user=request.user)
    all_tasks = day_tasks.count()
    if all_tasks == 0:
        return 0
    done_tasks = day_tasks.filter(status="done").count()
    return round(100 * done_tasks / all_tasks)

def statistics(user, period_start, period_end):
    today = date.today()

    period_tasks = Task.objects.filter(
        user=user,
        status="todo",
        planned_date__date__gte=period_start,
        planned_date__date__lte=period_end,
    ).select_related("category")

    is_overdue = Q(planned_date__date__lt=today) | Q(deadline__lt=today)

    overdue_tasks = Task.objects.filter(
        is_overdue,
        user=user,
        status="todo",
    ).select_related("category").order_by("planned_date")

    todo_tasks = period_tasks.exclude(is_overdue).order_by("planned_date")

    done_tasks = Task.objects.filter(
        user=user,
        status="done",
        status_changed_at__date__gte=period_start,
        status_changed_at__date__lte=period_end,
    ).select_related("category").order_by("-status_changed_at")

    return {
        "todo_tasks": todo_tasks,
        "done_tasks": done_tasks,
        "overdue_tasks": overdue_tasks,
    }


def chart_buckets(period, period_start, period_end):
    """Dzieli okres na kawałki: dni (tydzień) albo tygodnie (miesiąc, kwartał)."""
    day_names = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
    buckets = []

    if period == "week":
        day = period_start
        while day <= period_end:
            label = f"{day_names[day.weekday()]} {day:%d.%m}"
            buckets.append((day, day, label))
            day += timedelta(days=1)
    else:
        start = period_start
        while start <= period_end:
            end = min(start + timedelta(days=6 - start.weekday()), period_end)
            buckets.append((start, end, f"{start:%d.%m}–{end:%d.%m}"))
            start = end + timedelta(days=1)

    return buckets


def chart_data(user, period, period_start, period_end):
    today = date.today()
    is_overdue = Q(planned_date__date__lt=today) | Q(deadline__lt=today)

    period_todo = Task.objects.filter(
        user=user,
        status="todo",
        planned_date__date__gte=period_start,
        planned_date__date__lte=period_end,
    )
    period_done = Task.objects.filter(
        user=user,
        status="done",
        status_changed_at__date__gte=period_start,
        status_changed_at__date__lte=period_end,
    )

    def counts_by_day(queryset, date_field):
        rows = (queryset.annotate(day=TruncDate(date_field))
                        .values("day")
                        .annotate(count=Count("id")))
        return {row["day"]: row["count"] for row in rows}

    done_by_day = counts_by_day(period_done, "status_changed_at")
    todo_by_day = counts_by_day(period_todo.exclude(is_overdue), "planned_date")
    overdue_by_day = counts_by_day(period_todo.filter(is_overdue), "planned_date")

    labels, done, todo, overdue = [], [], [], []
    for start, end, label in chart_buckets(period, period_start, period_end):
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        labels.append(label)
        done.append(sum(done_by_day.get(d, 0) for d in days))
        todo.append(sum(todo_by_day.get(d, 0) for d in days))
        overdue.append(sum(overdue_by_day.get(d, 0) for d in days))

    return {
        "labels": labels,
        "done": done,
        "todo": todo,
        "overdue": overdue,
        "has_data": any(done) or any(todo) or any(overdue),
    }


def render_statistics(request, period, period_start, period_end):
    context = {
        "statistics": statistics(request.user, period_start, period_end),
        "chart": chart_data(request.user, period, period_start, period_end),
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
    }
    return render(request, "planner/statistics.html", context)

@login_required
def show_weekly_statistics(request):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return render_statistics(request, "week", week_start, week_end)

@login_required
def show_monthly_statistics(request):
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    month_end = next_month_start - timedelta(days=1)
    return render_statistics(request, "month", month_start, month_end)

@login_required
def show_quarterly_statistics(request):
    today = date.today()
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_start_month, 1)
    next_quarter_start_month = quarter_start_month + 3
    if next_quarter_start_month > 12:
        next_quarter_start = date(today.year + 1, 1, 1)
    else:
        next_quarter_start = date(today.year, next_quarter_start_month, 1)
    quarter_end = next_quarter_start - timedelta(days=1)
    return render_statistics(request, "quarter", quarter_start, quarter_end)

@login_required
def ai_kroki(request):
    kroki = []
    form = GoalForm()

    if request.method == "POST":
        akcja = request.POST.get("akcja")

        if akcja == "zaproponuj":
            form = GoalForm(request.POST)
            if form.is_valid():
                cel = form.cleaned_data["goal"]
                kroki = rozbij_cel_na_kroki(cel)

        elif akcja == "dodaj":
            wybrane = request.POST.getlist("kroki")
            data = request.POST.get("data")

            if not data:
                messages.error(request, "Wybierz datę, żeby dodać zadania.")
                return redirect("ai_kroki")

            # "2026-11-22" -> 22.11.2026, godz. 9:00, w strefie czasowej aplikacji
            try:
                planned_date = timezone.make_aware(
                    datetime.combine(date.fromisoformat(data), time(9, 0))
                )
            except ValueError:
                messages.error(request, "Nieprawidłowa data.")
                return redirect("ai_kroki")

            for krok in wybrane:
                Task.objects.create(
                    name=krok,
                    planned_date=planned_date,
                    duration_minutes=30,
                    user=request.user,
                )

            messages.success(request, f"Dodano {len(wybrane)} zadań")
            return redirect("home")

    return render(request, "planner/ai_kroki.html", {"form": form, "kroki": kroki})
