import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import Profile
from matching.models import MatchResult
from matching.services import (
    _compute_match,
    calculate_city_score,
    calculate_experience_score,
    calculate_match,
    calculate_skill_score,
    calculate_text_similarity,
)
from resumes.models import Resume, Skill
from vacancies.models import Vacancy


class MatchingServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        self.user.profile.role = Profile.Role.APPLICANT
        self.user.profile.save()

        recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        recruiter.profile.role = Profile.Role.RECRUITER
        recruiter.profile.save()

        self.s1 = Skill.objects.create(name='Python')
        self.s2 = Skill.objects.create(name='Django')
        self.s3 = Skill.objects.create(name='JavaScript')
        self.s4 = Skill.objects.create(name='React')

        self.resume = Resume.objects.create(
            owner=self.user,
            title='Backend Developer',
            full_name='Test Applicant',
            desired_position='Python Developer',
            city='Moscow',
            experience_years=Decimal('3.0'),
            search_status='looking',
            visibility='public',
            about='Experienced Python developer with Django background.',
            work_experience='3 years at Tech Corp building web apps.',
        )

        self.vacancy = Vacancy.objects.create(
            owner=recruiter,
            title='Python Backend Engineer',
            company='Test Company',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('3.0'),
            description='Looking for a Python Django developer.',
            visibility='public',
        )

        self.resume.skill_tags.set([self.s1, self.s2])
        self.vacancy.skill_tags.set([self.s1, self.s2])

    # ── Skill score tests ──────────────────────────────────────────────────────

    def test_skill_score_full_match(self):
        result = calculate_skill_score(self.resume, self.vacancy)
        self.assertEqual(result['score'], 1.0)

    def test_skill_score_partial_match(self):
        self.vacancy.skill_tags.set([self.s1, self.s2, self.s3, self.s4])
        result = calculate_skill_score(self.resume, self.vacancy)
        self.assertEqual(result['score'], 0.5)

    def test_skill_score_no_match(self):
        self.vacancy.skill_tags.set([self.s3, self.s4])
        result = calculate_skill_score(self.resume, self.vacancy)
        self.assertEqual(result['score'], 0.0)

    def test_skill_score_empty_vacancy_skills(self):
        self.vacancy.skill_tags.set([])
        result = calculate_skill_score(self.resume, self.vacancy)
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['matched_skills'], [])
        self.assertEqual(result['missing_skills'], [])

    # ── City score tests ───────────────────────────────────────────────────────

    def test_city_score_match(self):
        score = calculate_city_score(self.resume, self.vacancy)
        self.assertEqual(score, 1.0)

    def test_city_score_mismatch(self):
        self.vacancy.city = 'Saint Petersburg'
        self.vacancy.save()
        score = calculate_city_score(self.resume, self.vacancy)
        self.assertEqual(score, 0.0)

    def test_city_score_empty(self):
        self.vacancy.city = ''
        self.vacancy.save()
        score = calculate_city_score(self.resume, self.vacancy)
        self.assertEqual(score, 0.5)

    # ── Experience score tests ─────────────────────────────────────────────────

    def test_experience_score_sufficient(self):
        score = calculate_experience_score(self.resume, self.vacancy)
        self.assertEqual(score, 1.0)

    def test_experience_score_partial(self):
        self.resume.experience_years = Decimal('1.5')
        self.resume.save()
        score = calculate_experience_score(self.resume, self.vacancy)
        self.assertAlmostEqual(score, 0.5)

    def test_experience_score_no_requirement(self):
        self.vacancy.required_experience_years = Decimal('0')
        self.vacancy.save()
        score = calculate_experience_score(self.resume, self.vacancy)
        self.assertEqual(score, 1.0)

    # ── Text similarity tests ──────────────────────────────────────────────────

    def test_text_similarity_returns_float(self):
        score = calculate_text_similarity(self.resume, self.vacancy)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_text_similarity_empty_text(self):
        empty_resume = Resume.objects.create(
            owner=self.user,
            title='',
            full_name='',
            desired_position='',
            city='',
            experience_years=Decimal('0'),
            search_status='looking',
            visibility='public',
            education='',
            work_experience='',
            about='',
        )
        empty_vacancy = Vacancy.objects.create(
            owner=self.vacancy.owner,
            title='',
            company='',
            description='',
            employment_type='full_time',
            visibility='public',
        )
        score = calculate_text_similarity(empty_resume, empty_vacancy)
        self.assertEqual(score, 0.0)

    # ── _compute_match tests ───────────────────────────────────────────────────

    def test_compute_match_score_in_range(self):
        result = _compute_match(self.resume, self.vacancy)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 1.0)

    def test_compute_match_returns_required_keys(self):
        result = _compute_match(self.resume, self.vacancy)
        for key in ('score', 'score_percent', 'matched_skills', 'missing_skills', 'explanation', 'ai_used'):
            self.assertIn(key, result)


class MatchingCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='applicant@test.com',
            email='applicant@test.com',
            password='testpass123',
        )
        self.user.profile.role = Profile.Role.APPLICANT
        self.user.profile.save()

        recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='testpass123',
        )
        recruiter.profile.role = Profile.Role.RECRUITER
        recruiter.profile.save()

        self.resume = Resume.objects.create(
            owner=self.user,
            title='Cache Test Resume',
            full_name='Cache User',
            desired_position='Developer',
            city='Moscow',
            experience_years=Decimal('3.0'),
            search_status='looking',
            visibility='public',
        )

        self.vacancy = Vacancy.objects.create(
            owner=recruiter,
            title='Cache Test Vacancy',
            company='Cache Company',
            city='Moscow',
            employment_type='full_time',
            required_experience_years=Decimal('3.0'),
            description='Cache test description.',
            visibility='public',
        )

    def test_cache_hit(self):
        calculate_match(self.resume, self.vacancy)
        self.assertTrue(
            MatchResult.objects.filter(resume=self.resume, vacancy=self.vacancy).exists()
        )
        mr_first = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)
        calculated_at_first = mr_first.calculated_at

        calculate_match(self.resume, self.vacancy)

        self.assertEqual(MatchResult.objects.count(), 1)
        mr_second = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)
        self.assertEqual(calculated_at_first, mr_second.calculated_at)

    def test_cache_invalidation_on_resume_update(self):
        calculate_match(self.resume, self.vacancy)
        mr = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)

        # Backdate the cache so resume.updated_at will exceed it after save
        backdated = timezone.now() - datetime.timedelta(hours=1)
        MatchResult.objects.filter(pk=mr.pk).update(calculated_at=backdated)

        self.resume.save()  # updates resume.updated_at to now
        calculate_match(self.resume, self.vacancy)

        mr.refresh_from_db()
        self.assertGreater(mr.calculated_at, backdated)

    def test_cache_invalidation_on_vacancy_update(self):
        calculate_match(self.resume, self.vacancy)
        mr = MatchResult.objects.get(resume=self.resume, vacancy=self.vacancy)

        backdated = timezone.now() - datetime.timedelta(hours=1)
        MatchResult.objects.filter(pk=mr.pk).update(calculated_at=backdated)

        self.vacancy.save()  # updates vacancy.updated_at to now
        calculate_match(self.resume, self.vacancy)

        mr.refresh_from_db()
        self.assertGreater(mr.calculated_at, backdated)