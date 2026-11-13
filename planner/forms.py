from django import forms
from django.forms import ModelForm

from .models import PRIORITY_CHOICES, STATUS_CHOICES, Task, Category


class BootstrapMixin:
    """Dodaje klasy Bootstrapa do wszystkich pól formularza."""

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
    title = forms.CharField(max_length=100)
    planned_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'}
        )
    )
    deadline = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date'}
        ), required=False
    )
    duration_minutes = forms.IntegerField(required=True)
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES)
    status = forms.ChoiceField(choices=STATUS_CHOICES)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)


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
        widgets = {
            "planned_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "deadline": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }


class GoalForm(BootstrapMixin, forms.Form):
    goal = forms.CharField(max_length=200)