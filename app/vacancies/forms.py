from django import forms

from resumes.models import Resume, Skill
from .models import Vacancy, VacancyApplication


class VacancyForm(forms.ModelForm):
    skill_tags = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs={'class': 'tom-select'}),
        required=False,
        label='Требуемые навыки',
    )

    class Meta:
        model = Vacancy
        fields = [
            'title',
            'company',
            'city',
            'employment_type',
            'required_experience_years',
            'salary_from',
            'salary_to',
            'skill_tags',
            'description',
            'requirements',
            'conditions',
            'visibility',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Junior Python Developer'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название компании'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город'
            }),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'required_experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.5'
            }),
            'salary_from': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Например: 70000'
            }),
            'salary_to': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Например: 120000'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Опишите вакансию'
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Опишите требования к кандидату'
            }),
            'conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишите условия работы'
            }),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }


class VacancyApplicationForm(forms.ModelForm):
    class Meta:
        model = VacancyApplication
        fields = ['resume', 'cover_letter']

        widgets = {
            'resume': forms.Select(attrs={'class': 'form-select'}),
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Кратко напишите, почему вы подходите на эту вакансию'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields['resume'].queryset = Resume.objects.filter(owner=user)
            self.fields['resume'].empty_label = 'Выберите резюме'


class VacancyFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='Поиск',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название, компания, описание...'
        })
    )
    employment_type = forms.ChoiceField(
        required=False,
        label='Тип занятости',
        choices=[('', 'Любой')] + Vacancy.EmploymentType.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.CharField(
        required=False,
        label='Город',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Город'
        })
    )
    salary_min = forms.IntegerField(
        required=False,
        label='Зарплата от',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: 80000'
        })
    )
    skill = forms.CharField(
        required=False,
        label='Навык',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Python'
        })
    )