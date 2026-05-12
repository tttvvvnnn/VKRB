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


EXPERIENCE_CHOICES = [
    ('', 'Любой опыт'),
    ('0', 'Без опыта'),
    ('1', 'До 1 года'),
    ('3', 'До 3 лет'),
    ('6', 'До 6 лет'),
    ('6+', 'Более 6 лет'),
]

SORT_CHOICES = [
    ('-created_at', 'Сначала новые'),
    ('created_at',  'Сначала старые'),
    ('-salary_from', 'По убыванию зарплаты'),
    ('salary_from',  'По возрастанию зарплаты'),
    ('-required_experience_years', 'По убыванию опыта'),
]


class VacancyFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='Поиск',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Должность, компания, описание…',
        })
    )
    employment_type = forms.MultipleChoiceField(
        required=False,
        label='Тип занятости',
        choices=Vacancy.EmploymentType.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    city = forms.CharField(
        required=False,
        label='Город',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Москва',
        })
    )
    salary_min = forms.IntegerField(
        required=False,
        label='Зарплата от',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
        })
    )
    salary_max = forms.IntegerField(
        required=False,
        label='до',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '∞',
        })
    )
    has_salary = forms.BooleanField(
        required=False,
        label='Только с указанной зарплатой',
    )
    experience = forms.ChoiceField(
        required=False,
        label='Требуемый опыт',
        choices=EXPERIENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    skill = forms.CharField(
        required=False,
        label='Навык',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Python',
        })
    )
    with_source = forms.BooleanField(
        required=False,
        label='Только с Труд Всем',
    )
    sort_by = forms.ChoiceField(
        required=False,
        label='Сортировка',
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )