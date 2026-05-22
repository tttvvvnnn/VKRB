import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile
from matching.models import MatchResult
from resumes.models import Resume
from vacancies.models import FavoriteVacancy, Vacancy, VacancyApplication


class VacanciesTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        self.recruiter.profile.role = Profile.Role.RECRUITER
        self.recruiter.profile.save()

        self.applicant = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        self.applicant.profile.role = Profile.Role.APPLICANT
        self.applicant.profile.save()

        self.vacancy = Vacancy.objects.create(
            owner=self.recruiter,
            title='Python Developer',
            company='Test Company',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('2.0'),
            description='We are looking for a Python developer.',
            visibility='public',
        )

        self.resume = Resume.objects.create(
            owner=self.applicant,
            title='My Resume',
            full_name='Test Applicant',
            desired_position='Developer',
            city='Moscow',
            experience_years=Decimal('3.0'),
            search_status='looking',
            visibility='public',
        )

    def _vacancy_data(self, **overrides):
        data = {
            'title': 'New Vacancy',
            'company': 'Some Company',
            'city': 'Moscow',
            'employment_type': 'full_time',
            'required_experience_years': '1',
            'description': 'Job description here.',
            'requirements': '',
            'conditions': '',
            'visibility': 'public',
        }
        data.update(overrides)
        return data

    def test_create_vacancy(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(reverse('vacancy_create'), self._vacancy_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vacancy.objects.filter(owner=self.recruiter, title='New Vacancy').exists())

    def test_create_vacancy_blocked_for_applicant(self):
        self.client.force_login(self.applicant)
        response = self.client.post(reverse('vacancy_create'), self._vacancy_data())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Vacancy.objects.filter(owner=self.applicant).exists())

    def test_apply_to_vacancy(self):
        self.client.force_login(self.applicant)
        response = self.client.post(
            reverse('vacancy_apply', args=[self.vacancy.pk]),
            {'resume': self.resume.pk, 'cover_letter': 'I am a great fit.'},
        )
        self.assertEqual(response.status_code, 302)
        application = VacancyApplication.objects.filter(
            vacancy=self.vacancy,
            resume=self.resume,
            applicant=self.applicant,
        )
        self.assertTrue(application.exists())
        self.assertEqual(application.first().status, 'new')

    def test_apply_duplicate_blocked(self):
        self.client.force_login(self.applicant)
        self.client.post(
            reverse('vacancy_apply', args=[self.vacancy.pk]),
            {'resume': self.resume.pk, 'cover_letter': 'First application.'},
        )
        self.client.post(
            reverse('vacancy_apply', args=[self.vacancy.pk]),
            {'resume': self.resume.pk, 'cover_letter': 'Second application.'},
        )
        count = VacancyApplication.objects.filter(
            vacancy=self.vacancy,
            resume=self.resume,
            applicant=self.applicant,
        ).count()
        self.assertEqual(count, 1)

    def test_toggle_favorite_add(self):
        self.client.force_login(self.applicant)
        response = self.client.post(reverse('toggle_favorite_vacancy', args=[self.vacancy.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['favorited'])
        self.assertTrue(
            FavoriteVacancy.objects.filter(user=self.applicant, vacancy=self.vacancy).exists()
        )

    def test_toggle_favorite_remove(self):
        FavoriteVacancy.objects.create(user=self.applicant, vacancy=self.vacancy)
        self.client.force_login(self.applicant)
        response = self.client.post(reverse('toggle_favorite_vacancy', args=[self.vacancy.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['favorited'])
        self.assertFalse(
            FavoriteVacancy.objects.filter(user=self.applicant, vacancy=self.vacancy).exists()
        )

    def test_matchresult_unique_constraint(self):
        MatchResult.objects.update_or_create(
            resume=self.resume,
            vacancy=self.vacancy,
            defaults={
                'score': 0.5,
                'score_percent': 50.0,
                'skill_score_percent': 50.0,
                'text_score_percent': 50.0,
                'experience_score_percent': 50.0,
                'city_score_percent': 50.0,
                'explanation': 'initial',
                'ai_used': False,
            },
        )
        MatchResult.objects.update_or_create(
            resume=self.resume,
            vacancy=self.vacancy,
            defaults={
                'score': 0.8,
                'score_percent': 80.0,
                'skill_score_percent': 80.0,
                'text_score_percent': 80.0,
                'experience_score_percent': 80.0,
                'city_score_percent': 80.0,
                'explanation': 'updated',
                'ai_used': False,
            },
        )
        self.assertEqual(
            MatchResult.objects.filter(resume=self.resume, vacancy=self.vacancy).count(), 1
        )
        mr = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)
        self.assertEqual(mr.score_percent, 80.0)