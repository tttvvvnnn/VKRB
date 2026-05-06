from django import forms

from .models import Resume


class ResumeForm(forms.ModelForm):
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
            'skills',
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
            'skills': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Например: Python, Django, SQL, Git'
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
            'search_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            }),
        }