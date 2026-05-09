from django import forms

from resumes.models import Resume, Skill


class ResumeForm(forms.ModelForm):
    skill_tags = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs={'class': 'tom-select'}),
        required=False,
        label='Навыки',
    )

    class Meta:
        model = Resume
        fields = [
            'title',
            'full_name',
            'desired_position',
            'city',
            'email',
            'phone',
            'experience_years',
            'education',
            'skill_tags',
            'work_experience',
            'about',
            'search_status',
            'visibility',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Python-разработчик'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ФИО кандидата'
            }),
            'desired_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Backend-разработчик'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email для связи'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Телефон'
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.5'
            }),
            'education': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите образование'
            }),
            'work_experience': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Опишите опыт работы'
            }),
            'about': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Дополнительная информация о кандидате'
            }),
            'search_status': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }


class ResumeFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='Поиск',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Должность, навык...'
        })
    )
    city = forms.CharField(
        required=False,
        label='Город',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Город'
        })
    )
    search_status = forms.ChoiceField(
        required=False,
        label='Статус поиска',
        choices=[('', 'Любой')] + Resume.SearchStatus.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    skill = forms.CharField(
        required=False,
        label='Навык',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Python'
        })
    )