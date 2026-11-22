from django import forms
from django.forms import ModelForm

from .models import PRIORITY_CHOICES, Task, Category


class BootstrapMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class AddTask(BootstrapMixin, forms.Form):
    title = forms.CharField(max_length=100, label="Nazwa zadania")
    planned_date = forms.DateTimeField(
        label="Planowana data",
        widget=forms.DateTimeInput(
            attrs={"data-picker": "datetime"},
            format="%Y-%m-%d %H:%M",
        ),
    )
    deadline = forms.DateField(
        label="Termin",
        widget=forms.DateInput(
            attrs={"data-picker": "date"},
            format="%Y-%m-%d",
        ),
        required=False,
    )
    duration_minutes = forms.IntegerField(label="Czas trwania (min)", required=True)
    priority = forms.ChoiceField(label="Priorytet", choices=PRIORITY_CHOICES)
    category = forms.ModelChoiceField(
        label="Kategoria",
        queryset=Category.objects.all(),
        required=False,
        empty_label="Bez kategorii",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user)


class EditTask(BootstrapMixin, ModelForm):
    class Meta:
        model = Task
        fields = [
            "name",
            "planned_date",
            "deadline",
            "duration_minutes",
            "priority",
            "status",
            "category",
        ]
        labels = {
            "name": "Nazwa zadania",
            "planned_date": "Planowana data",
            "deadline": "Termin",
            "duration_minutes": "Czas trwania (min)",
            "priority": "Priorytet",
            "status": "Status",
            "category": "Kategoria",
        }
        widgets = {
            "planned_date": forms.DateTimeInput(
                attrs={"data-picker": "datetime"},
                format="%Y-%m-%d %H:%M",
            ),
            "deadline": forms.DateInput(
                attrs={"data-picker": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "Bez kategorii"
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user)


class GoalForm(BootstrapMixin, forms.Form):
    goal = forms.CharField(max_length=200, label="Twój cel")