from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile


class AccountsTests(TestCase):
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

    def test_register_applicant(self):
        response = self.client.post(reverse('register'), {
            'email': 'newapplicant@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'applicant',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='newapplicant@test.com')
        self.assertEqual(user.profile.role, 'applicant')

    def test_register_recruiter(self):
        response = self.client.post(reverse('register'), {
            'email': 'newrecruiter@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'recruiter',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='newrecruiter@test.com')
        self.assertEqual(user.profile.role, 'recruiter')

    def test_register_duplicate_email(self):
        initial_count = User.objects.count()
        response = self.client.post(reverse('register'), {
            'email': 'applicant@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'applicant',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), initial_count)

    def test_login_valid(self):
        response = self.client.post(reverse('login'), {
            'username': 'applicant@test.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {
            'username': 'applicant@test.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_profile_created_on_register(self):
        self.client.post(reverse('register'), {
            'email': 'profiletest@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'applicant',
        })
        user = User.objects.get(email='profiletest@test.com')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_recruiter_required_blocks_applicant(self):
        self.client.force_login(self.applicant)
        response = self.client.get(reverse('vacancy_create'))
        self.assertEqual(response.status_code, 302)

    def test_applicant_required_blocks_recruiter(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse('resume_create'))
        self.assertEqual(response.status_code, 302)