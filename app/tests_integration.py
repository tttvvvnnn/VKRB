"""
Комплексные интеграционные тесты.
Каждый класс проверяет сквозной сценарий, а не отдельную функцию.
"""
import datetime
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from matching.models import MatchResult
from matching.services import calculate_match, rank_resumes_for_vacancy
from resumes.models import Resume, Skill
from vacancies.models import FavoriteVacancy, Vacancy, VacancyApplication


class ApplicantFullCycleTest(TestCase):
    """
    Регистрация → резюме → сопоставление → избранное → отклик.
    Все объекты созданы корректно, результат сопоставления ненулевой.
    """

    def setUp(self):
        self.client = Client()
        self.skill = Skill.objects.create(name='Python')

        recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        recruiter.profile.role = Profile.Role.RECRUITER
        recruiter.profile.save()

        self.vacancy = Vacancy.objects.create(
            owner=recruiter,
            title='Python Developer',
            company='Test Company',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('2.0'),
            description='Looking for a Python developer.',
            visibility='public',
        )
        self.vacancy.skill_tags.set([self.skill])

    def test_full_applicant_cycle(self):
        # Шаг 1: регистрация соискателя
        response = self.client.post(reverse('register'), {
            'email': 'applicant@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'applicant',
        })
        self.assertEqual(response.status_code, 302)
        applicant = User.objects.get(email='applicant@test.com')
        self.assertEqual(applicant.profile.role, 'applicant')

        self.client.force_login(applicant)

        # Шаг 2: создание резюме
        response = self.client.post(reverse('resume_create'), {
            'title': 'Python CV',
            'full_name': 'Ivan Petrov',
            'desired_position': 'Python Developer',
            'city': 'Moscow',
            'experience_years': '3',
            'search_status': 'looking',
            'visibility': 'public',
            'education': '',
            'work_experience': '',
            'about': '',
            'email': '',
            'phone': '',
        })
        self.assertEqual(response.status_code, 302)
        resume = Resume.objects.get(owner=applicant)
        self.assertEqual(resume.title, 'Python CV')

        # Добавляем совпадающий навык для ненулевого балла
        resume.skill_tags.set([self.skill])

        # Шаг 3: сопоставление резюме с вакансией
        result = calculate_match(resume, self.vacancy)
        self.assertIn('score', result)
        self.assertGreater(result['score'], 0,
                           msg='Балл сопоставления должен быть больше 0 при совпадающих навыках')
        self.assertLessEqual(result['score'], 1.0)
        self.assertTrue(
            MatchResult.objects.filter(resume=resume, vacancy=self.vacancy).exists()
        )

        # Шаг 4: добавление вакансии в избранное
        response = self.client.post(
            reverse('toggle_favorite_vacancy', args=[self.vacancy.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['favorited'])
        self.assertTrue(
            FavoriteVacancy.objects.filter(user=applicant, vacancy=self.vacancy).exists()
        )

        # Шаг 5: отклик на вакансию
        response = self.client.post(
            reverse('vacancy_apply', args=[self.vacancy.pk]),
            {'resume': resume.pk, 'cover_letter': 'I am a great Python developer!'},
        )
        self.assertEqual(response.status_code, 302)
        application = VacancyApplication.objects.filter(
            vacancy=self.vacancy, applicant=applicant
        )
        self.assertTrue(application.exists())
        self.assertEqual(application.first().status, 'new')


class RecruiterFullCycleTest(TestCase):
    """
    Регистрация → вакансия → сопоставление → просмотр откликов → изменение статуса.
    Ранжирование корректно, статус отклика обновлён.
    """

    def setUp(self):
        self.client = Client()
        self.skill = Skill.objects.create(name='Python')

        self.applicant = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        self.applicant.profile.role = Profile.Role.APPLICANT
        self.applicant.profile.save()

        self.resume = Resume.objects.create(
            owner=self.applicant,
            title='Python Developer CV',
            full_name='Ivan Petrov',
            desired_position='Python Developer',
            city='Moscow',
            experience_years=Decimal('3.0'),
            search_status='looking',
            visibility='public',
        )
        self.resume.skill_tags.set([self.skill])

    def test_full_recruiter_cycle(self):
        # Шаг 1: регистрация рекрутера
        response = self.client.post(reverse('register'), {
            'email': 'recruiter@test.com',
            'password1': 'complexpass456!',
            'password2': 'complexpass456!',
            'role': 'recruiter',
        })
        self.assertEqual(response.status_code, 302)
        recruiter = User.objects.get(email='recruiter@test.com')
        self.assertEqual(recruiter.profile.role, 'recruiter')

        self.client.force_login(recruiter)

        # Шаг 2: создание вакансии
        response = self.client.post(reverse('vacancy_create'), {
            'title': 'Python Backend Engineer',
            'company': 'Tech Corp',
            'city': 'Moscow',
            'employment_type': 'full_time',
            'required_experience_years': '2',
            'description': 'Looking for a Python developer.',
            'requirements': '',
            'conditions': '',
            'visibility': 'public',
        })
        self.assertEqual(response.status_code, 302)
        vacancy = Vacancy.objects.get(owner=recruiter)
        vacancy.skill_tags.set([self.skill])

        # Шаг 3: сопоставление вакансии с резюме
        result = calculate_match(self.resume, vacancy)
        self.assertGreater(result['score'], 0)

        # Проверяем ранжирование: резюме отсортированы по убыванию балла
        rankings = rank_resumes_for_vacancy(vacancy, Resume.objects.all())
        self.assertGreaterEqual(len(rankings), 1)
        self.assertIn('score', rankings[0])
        self.assertIn('resume', rankings[0])
        self.assertGreater(rankings[0]['score'], 0)
        # Убеждаемся, что список отсортирован по убыванию
        scores = [r['score'] for r in rankings]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Шаг 4: соискатель откликается, рекрутер просматривает список
        application = VacancyApplication.objects.create(
            vacancy=vacancy,
            resume=self.resume,
            applicant=self.applicant,
            status='new',
        )
        response = self.client.get(reverse('application_list'))
        self.assertEqual(response.status_code, 200)

        # Шаг 5: рекрутер меняет статус отклика new → viewed
        response = self.client.post(
            reverse('application_status_update', args=[application.pk, 'viewed'])
        )
        self.assertEqual(response.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, 'viewed')

        # Шаг 6: рекрутер принимает отклик viewed → accepted
        response = self.client.post(
            reverse('application_status_update', args=[application.pk, 'accepted'])
        )
        self.assertEqual(response.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, 'accepted')


class MatchResultCachingIntegrationTest(TestCase):
    """
    Повторный вызов calculate_match использует кэш.
    Изменение резюме или вакансии инвалидирует кэш и запускает пересчёт.
    """

    def setUp(self):
        applicant = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        applicant.profile.role = Profile.Role.APPLICANT
        applicant.profile.save()

        recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        recruiter.profile.role = Profile.Role.RECRUITER
        recruiter.profile.save()

        self.skill1 = Skill.objects.create(name='Python')
        self.skill2 = Skill.objects.create(name='Django')

        self.resume = Resume.objects.create(
            owner=applicant,
            title='Developer',
            full_name='Test User',
            desired_position='Developer',
            city='Moscow',
            experience_years=Decimal('3.0'),
            search_status='looking',
            visibility='public',
        )
        self.resume.skill_tags.set([self.skill1])

        self.vacancy = Vacancy.objects.create(
            owner=recruiter,
            title='Python Dev',
            company='Corp',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('3.0'),
            description='Python position.',
            visibility='public',
        )
        self.vacancy.skill_tags.set([self.skill1, self.skill2])

    def test_cache_hit_then_invalidation_on_resume_change(self):
        # Первый вызов — вычисляет и сохраняет в MatchResult
        result1 = calculate_match(self.resume, self.vacancy)
        self.assertEqual(MatchResult.objects.count(), 1)
        mr = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)
        score_initial = mr.score
        calculated_at_1 = mr.calculated_at

        # Второй вызов без изменений — возвращает кэш, calculated_at не меняется
        result2 = calculate_match(self.resume, self.vacancy)
        self.assertEqual(MatchResult.objects.count(), 1)
        mr.refresh_from_db()
        self.assertEqual(mr.calculated_at, calculated_at_1,
                         msg='Повторный вызов не должен обновлять calculated_at (кэш)')
        self.assertEqual(result1['score'], result2['score'])

        # Инвалидируем кэш: backdating calculated_at в прошлое
        backdated = timezone.now() - datetime.timedelta(hours=1)
        MatchResult.objects.filter(pk=mr.pk).update(calculated_at=backdated)

        # Добавляем недостающий навык → score должен вырасти после пересчёта
        self.resume.skill_tags.add(self.skill2)
        self.resume.save()  # обновляет updated_at

        # Третий вызов — кэш устарел, происходит пересчёт
        result3 = calculate_match(self.resume, self.vacancy)
        self.assertEqual(MatchResult.objects.count(), 1)  # по-прежнему одна запись
        mr.refresh_from_db()
        self.assertGreater(mr.calculated_at, backdated,
                           msg='calculated_at должен обновиться после пересчёта')
        self.assertGreaterEqual(result3['score'], score_initial,
                                msg='Балл должен вырасти после добавления недостающего навыка')

    def test_cache_invalidation_on_vacancy_change(self):
        calculate_match(self.resume, self.vacancy)
        mr = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)

        backdated = timezone.now() - datetime.timedelta(hours=1)
        MatchResult.objects.filter(pk=mr.pk).update(calculated_at=backdated)

        self.vacancy.city = 'Saint Petersburg'  # меняем город → city_score упадёт
        self.vacancy.save()

        calculate_match(self.resume, self.vacancy)
        mr.refresh_from_db()
        self.assertGreater(mr.calculated_at, backdated,
                           msg='calculated_at должен обновиться после изменения вакансии')


class RoleAccessControlTest(TestCase):
    """
    Все запрещённые действия перехватываются декораторами recruiter_required / applicant_required.
    Неаутентифицированный пользователь перенаправляется на логин.
    """

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

        self.resume = Resume.objects.create(
            owner=self.applicant,
            title='CV',
            full_name='Applicant User',
            desired_position='Developer',
            city='Moscow',
            experience_years=Decimal('1.0'),
            search_status='looking',
            visibility='public',
        )

        self.vacancy = Vacancy.objects.create(
            owner=self.recruiter,
            title='Dev Position',
            company='Corp',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('1.0'),
            description='Dev role.',
            visibility='public',
        )

    def test_recruiter_blocked_from_applicant_actions(self):
        self.client.force_login(self.recruiter)

        # Создание резюме — запрещено для рекрутера
        response = self.client.get(reverse('resume_create'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Resume.objects.filter(owner=self.recruiter).exists())

        # Отклик на вакансию — запрещён для рекрутера
        response = self.client.post(
            reverse('vacancy_apply', args=[self.vacancy.pk]),
            {'resume': self.resume.pk, 'cover_letter': 'test'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            VacancyApplication.objects.filter(applicant=self.recruiter).exists()
        )

        # Страница сопоставления резюме — только для соискателей
        response = self.client.get(
            reverse('match_vacancies_for_resume', args=[self.resume.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_applicant_blocked_from_recruiter_actions(self):
        self.client.force_login(self.applicant)

        # Создание вакансии — запрещено для соискателя
        response = self.client.get(reverse('vacancy_create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vacancy.objects.filter(owner=self.applicant).count(), 0)

        # Редактирование чужой вакансии — recruiter_required блокирует
        response = self.client.post(
            reverse('vacancy_update', args=[self.vacancy.pk]),
            {
                'title': 'Hacked Title',
                'company': 'Hacked Co',
                'description': 'Hacked',
                'employment_type': 'full_time',
                'visibility': 'public',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.vacancy.refresh_from_db()
        self.assertNotEqual(self.vacancy.title, 'Hacked Title')

        # Удаление чужой вакансии — recruiter_required блокирует
        response = self.client.post(reverse('vacancy_delete', args=[self.vacancy.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vacancy.objects.filter(pk=self.vacancy.pk).exists())

    def test_unauthenticated_blocked_from_protected_views(self):
        protected_urls = [
            reverse('resume_list'),
            reverse('resume_create'),
            reverse('vacancy_list'),
            reverse('vacancy_create'),
            reverse('matching_dashboard'),
            reverse('application_list'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                msg=f'Ожидался редирект на логин для {url}, получен {response.status_code}',
            )