from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile
from resumes.models import Resume


class ResumesTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.applicant = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        self.applicant.profile.role = Profile.Role.APPLICANT
        self.applicant.profile.save()

        self.recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        self.recruiter.profile.role = Profile.Role.RECRUITER
        self.recruiter.profile.save()

        self.applicant2 = User.objects.create_user(
            username='applicant2@test.com',
            email='applicant2@test.com',
            password='testpass123',
        )
        self.applicant2.profile.role = Profile.Role.APPLICANT
        self.applicant2.profile.save()

        self.resume = Resume.objects.create(
            owner=self.applicant,
            title='Test Resume',
            full_name='Test Applicant',
            desired_position='Developer',
            city='Moscow',
            experience_years=Decimal('1.0'),
            search_status='looking',
            visibility='public',
        )

    def _resume_data(self, **overrides):
        data = {
            'title': 'My Resume',
            'full_name': 'Test User',
            'desired_position': 'Python Developer',
            'city': 'Moscow',
            'experience_years': '1',
            'visibility': 'public',
            'search_status': 'looking',
            'education': '',
            'work_experience': '',
            'about': '',
            'email': '',
            'phone': '',
        }
        data.update(overrides)
        return data

    def test_create_resume(self):
        self.client.force_login(self.applicant)
        response = self.client.post(reverse('resume_create'), self._resume_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Resume.objects.filter(owner=self.applicant, title='My Resume').exists())

    def test_create_resume_blocked_for_recruiter(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(reverse('resume_create'), self._resume_data())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Resume.objects.filter(owner=self.recruiter).exists())

    def test_edit_own_resume(self):
        self.client.force_login(self.applicant)
        response = self.client.post(
            reverse('resume_update', args=[self.resume.pk]),
            self._resume_data(title='Updated Title'),
        )
        self.assertEqual(response.status_code, 302)
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.title, 'Updated Title')

    def test_edit_foreign_resume(self):
        self.client.force_login(self.applicant2)
        response = self.client.post(
            reverse('resume_update', args=[self.resume.pk]),
            self._resume_data(title='Hacked Title'),
        )
        self.assertEqual(response.status_code, 404)
        self.resume.refresh_from_db()
        self.assertNotEqual(self.resume.title, 'Hacked Title')

    def test_delete_own_resume(self):
        self.client.force_login(self.applicant)
        response = self.client.post(reverse('resume_delete', args=[self.resume.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Resume.objects.filter(pk=self.resume.pk).exists())

    def test_delete_foreign_resume(self):
        self.client.force_login(self.applicant2)
        response = self.client.post(reverse('resume_delete', args=[self.resume.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Resume.objects.filter(pk=self.resume.pk).exists())

    def test_public_resume_visible_to_stranger(self):
        self.resume.visibility = 'public'
        self.resume.save()
        self.client.force_login(self.applicant2)
        response = self.client.get(reverse('resume_detail', args=[self.resume.pk]))
        self.assertEqual(response.status_code, 200)

    def test_hidden_resume_blocked_for_stranger(self):
        self.resume.visibility = 'hidden'
        self.resume.save()
        self.client.force_login(self.applicant2)
        response = self.client.get(reverse('resume_detail', args=[self.resume.pk]))
        self.assertEqual(response.status_code, 404)

    def test_hidden_resume_visible_to_owner(self):
        self.resume.visibility = 'hidden'
        self.resume.save()
        self.client.force_login(self.applicant)
        response = self.client.get(reverse('resume_detail', args=[self.resume.pk]))
        self.assertEqual(response.status_code, 200)