from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Profile
from resumes.models import Resume
from vacancies.models import Vacancy, VacancyApplication


class Command(BaseCommand):
    help = 'Заполняет базу демонстрационными пользователями, резюме, вакансиями и откликами.'

    @transaction.atomic
    def handle(self, *args, **options):
        demo_emails = [
            'recruiter.it@example.com',
            'recruiter.hr@example.com',
            'ivan.petrov@example.com',
            'anna.smirnova@example.com',
            'dmitry.sokolov@example.com',
            'maria.kuznetsova@example.com',
            'sergey.volkov@example.com',
            'elena.orlova@example.com',
        ]

        User.objects.filter(email__in=demo_emails).delete()

        recruiter_it = self.create_user(
            email='recruiter.it@example.com',
            password='DemoPassword123',
            role=Profile.Role.RECRUITER,
            first_name='Алексей',
            last_name='Морозов',
        )

        recruiter_hr = self.create_user(
            email='recruiter.hr@example.com',
            password='DemoPassword123',
            role=Profile.Role.RECRUITER,
            first_name='Ольга',
            last_name='Васильева',
        )

        ivan = self.create_user(
            email='ivan.petrov@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Иван',
            last_name='Петров',
        )

        anna = self.create_user(
            email='anna.smirnova@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Анна',
            last_name='Смирнова',
        )

        dmitry = self.create_user(
            email='dmitry.sokolov@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Дмитрий',
            last_name='Соколов',
        )

        maria = self.create_user(
            email='maria.kuznetsova@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Мария',
            last_name='Кузнецова',
        )

        sergey = self.create_user(
            email='sergey.volkov@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Сергей',
            last_name='Волков',
        )

        elena = self.create_user(
            email='elena.orlova@example.com',
            password='DemoPassword123',
            role=Profile.Role.APPLICANT,
            first_name='Елена',
            last_name='Орлова',
        )

        resumes = {}

        resumes['ivan_python'] = Resume.objects.create(
            owner=ivan,
            title='Python-разработчик Django',
            full_name='Петров Иван Сергеевич',
            desired_position='Backend-разработчик Python',
            city='Москва',
            email='ivan.petrov@example.com',
            phone='+7 900 111-22-33',
            experience_years=Decimal('1.5'),
            education='Бакалавриат по направлению информатика и вычислительная техника.',
            skills='Python, Django, SQL, SQLite, PostgreSQL, REST API, Git, HTML, CSS',
            work_experience=(
                'Разработка учебных и коммерческих веб-приложений на Django. '
                'Создание моделей базы данных, настройка маршрутов, шаблонов, форм и административной панели. '
                'Опыт работы с SQL-запросами и REST API.'
            ),
            about='Интересуется backend-разработкой, автоматизацией бизнес-процессов и обработкой данных.',
            search_status=Resume.SearchStatus.LOOKING,
            visibility=Resume.Visibility.PUBLIC,
        )

        resumes['anna_frontend'] = Resume.objects.create(
            owner=anna,
            title='Frontend-разработчик JavaScript',
            full_name='Смирнова Анна Андреевна',
            desired_position='Frontend-разработчик',
            city='Санкт-Петербург',
            email='anna.smirnova@example.com',
            phone='+7 900 222-33-44',
            experience_years=Decimal('2.0'),
            education='Высшее образование, прикладная информатика.',
            skills='HTML, CSS, JavaScript, Bootstrap, React, Git, Figma, REST API',
            work_experience=(
                'Верстка адаптивных интерфейсов, разработка клиентской логики на JavaScript, '
                'работа с REST API и компонентным подходом.'
            ),
            about='Сильные стороны: аккуратная верстка, внимание к деталям, понимание UX.',
            search_status=Resume.SearchStatus.OPEN_TO_OFFERS,
            visibility=Resume.Visibility.PUBLIC,
        )

        resumes['dmitry_qa'] = Resume.objects.create(
            owner=dmitry,
            title='Тестировщик ПО',
            full_name='Соколов Дмитрий Павлович',
            desired_position='QA Engineer',
            city='Москва',
            email='dmitry.sokolov@example.com',
            phone='+7 900 333-44-55',
            experience_years=Decimal('1.0'),
            education='Среднее профессиональное образование, информационные системы.',
            skills='Manual Testing, Test Cases, Bug Reports, SQL, Postman, Jira, Git',
            work_experience=(
                'Функциональное тестирование веб-приложений, составление тест-кейсов, '
                'оформление баг-репортов, проверка API через Postman.'
            ),
            about='Готов развиваться в автоматизированном тестировании.',
            search_status=Resume.SearchStatus.LOOKING,
            visibility=Resume.Visibility.PUBLIC,
        )

        resumes['maria_data'] = Resume.objects.create(
            owner=maria,
            title='Аналитик данных',
            full_name='Кузнецова Мария Игоревна',
            desired_position='Data Analyst',
            city='Казань',
            email='maria.kuznetsova@example.com',
            phone='+7 900 444-55-66',
            experience_years=Decimal('2.5'),
            education='Высшее образование, бизнес-информатика.',
            skills='Python, SQL, Pandas, Excel, Power BI, Data Analysis, Statistics',
            work_experience=(
                'Подготовка отчетов, анализ данных, построение дашбордов, очистка данных с помощью Python и Pandas.'
            ),
            about='Интересуется аналитикой HR-данных и рекомендательными системами.',
            search_status=Resume.SearchStatus.OPEN_TO_OFFERS,
            visibility=Resume.Visibility.PUBLIC,
        )

        resumes['sergey_devops'] = Resume.objects.create(
            owner=sergey,
            title='Junior DevOps инженер',
            full_name='Волков Сергей Николаевич',
            desired_position='DevOps Engineer',
            city='Москва',
            email='sergey.volkov@example.com',
            phone='+7 900 555-66-77',
            experience_years=Decimal('1.0'),
            education='Бакалавриат, программная инженерия.',
            skills='Linux, Docker, Docker Compose, Git, CI/CD, Nginx, Bash, Python',
            work_experience=(
                'Настройка контейнеров Docker, запуск веб-приложений, базовая настройка Nginx, '
                'автоматизация задач с помощью Bash.'
            ),
            about='Хочет развиваться в инфраструктуре и развёртывании веб-приложений.',
            search_status=Resume.SearchStatus.LOOKING,
            visibility=Resume.Visibility.PUBLIC,
        )

        resumes['elena_hidden'] = Resume.objects.create(
            owner=elena,
            title='HR-специалист',
            full_name='Орлова Елена Максимовна',
            desired_position='HR Specialist',
            city='Москва',
            email='elena.orlova@example.com',
            phone='+7 900 666-77-88',
            experience_years=Decimal('3.0'),
            education='Высшее образование, управление персоналом.',
            skills='Recruitment, HR, Interview, Communication, Excel',
            work_experience='Подбор персонала, проведение интервью, ведение базы кандидатов.',
            about='Резюме скрыто и не должно попадать в публичный подбор.',
            search_status=Resume.SearchStatus.NOT_LOOKING,
            visibility=Resume.Visibility.HIDDEN,
        )

        vacancies = {}

        vacancies['python_junior'] = Vacancy.objects.create(
            owner=recruiter_it,
            title='Junior Python Developer',
            company='TechStaff Solutions',
            city='Москва',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('1.0'),
            salary_from=80000,
            salary_to=130000,
            skills='Python, Django, SQL, REST API, Git, HTML, CSS',
            description=(
                'Требуется junior backend-разработчик для участия в разработке веб-приложений '
                'на Django и поддержки существующих сервисов.'
            ),
            requirements=(
                'Знание Python, Django, основ SQL, понимание клиент-серверной архитектуры, '
                'умение работать с Git.'
            ),
            conditions='Офис или гибридный формат, наставник, участие в реальных проектах.',
            visibility=Vacancy.Visibility.PUBLIC,
        )

        vacancies['frontend'] = Vacancy.objects.create(
            owner=recruiter_it,
            title='Frontend Developer',
            company='WebInterface Lab',
            city='Санкт-Петербург',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('1.5'),
            salary_from=90000,
            salary_to=150000,
            skills='HTML, CSS, JavaScript, React, Bootstrap, Git, REST API',
            description='Разработка интерфейсов для веб-приложений и внутренних корпоративных систем.',
            requirements='Опыт адаптивной верстки, знание JavaScript, понимание работы REST API.',
            conditions='Гибкий график, возможность частично удалённой работы.',
            visibility=Vacancy.Visibility.PUBLIC,
        )

        vacancies['qa'] = Vacancy.objects.create(
            owner=recruiter_hr,
            title='QA Engineer',
            company='QualityPoint',
            city='Москва',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('1.0'),
            salary_from=70000,
            salary_to=110000,
            skills='Manual Testing, Test Cases, Bug Reports, SQL, Postman, Jira',
            description='Тестирование веб-приложений, проверка пользовательских сценариев и API.',
            requirements='Знание техник тест-дизайна, опыт оформления баг-репортов, базовый SQL.',
            conditions='Официальное оформление, обучение автоматизации тестирования.',
            visibility=Vacancy.Visibility.PUBLIC,
        )

        vacancies['data_analyst'] = Vacancy.objects.create(
            owner=recruiter_hr,
            title='Data Analyst',
            company='DataVision',
            city='Казань',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('2.0'),
            salary_from=100000,
            salary_to=160000,
            skills='Python, SQL, Pandas, Excel, Power BI, Data Analysis',
            description='Анализ данных, подготовка отчетности, построение дашбордов и поиск закономерностей.',
            requirements='Опыт SQL, Python/Pandas, понимание статистики, умение визуализировать данные.',
            conditions='Гибридный формат, профессиональное развитие, работа с большими массивами данных.',
            visibility=Vacancy.Visibility.PUBLIC,
        )

        vacancies['devops'] = Vacancy.objects.create(
            owner=recruiter_it,
            title='Junior DevOps Engineer',
            company='CloudDeploy',
            city='Москва',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('1.0'),
            salary_from=90000,
            salary_to=140000,
            skills='Linux, Docker, Docker Compose, Git, CI/CD, Nginx, Bash',
            description='Поддержка инфраструктуры веб-приложений, контейнеризация и настройка окружений.',
            requirements='Базовые знания Linux, Docker, Git, понимание принципов CI/CD.',
            conditions='Работа в команде разработки, обучение, возможность роста до Middle DevOps.',
            visibility=Vacancy.Visibility.PUBLIC,
        )

        vacancies['hidden_python'] = Vacancy.objects.create(
            owner=recruiter_it,
            title='Middle Python Developer — скрытая вакансия',
            company='Internal Project',
            city='Москва',
            employment_type=Vacancy.EmploymentType.FULL_TIME,
            required_experience_years=Decimal('3.0'),
            salary_from=180000,
            salary_to=250000,
            skills='Python, Django, PostgreSQL, Redis, Celery, Docker',
            description='Скрытая тестовая вакансия, не должна отображаться другим пользователям.',
            requirements='Опыт промышленной разработки от 3 лет.',
            conditions='Внутренний проект.',
            visibility=Vacancy.Visibility.HIDDEN,
        )

        VacancyApplication.objects.create(
            vacancy=vacancies['python_junior'],
            resume=resumes['ivan_python'],
            applicant=ivan,
            cover_letter='Здравствуйте. Меня заинтересовала вакансия, так как у меня есть опыт разработки на Django и SQL.',
            status=VacancyApplication.Status.NEW,
        )

        VacancyApplication.objects.create(
            vacancy=vacancies['qa'],
            resume=resumes['dmitry_qa'],
            applicant=dmitry,
            cover_letter='Готов рассмотреть вакансию QA Engineer. Есть опыт тестирования API через Postman.',
            status=VacancyApplication.Status.VIEWED,
        )

        VacancyApplication.objects.create(
            vacancy=vacancies['data_analyst'],
            resume=resumes['maria_data'],
            applicant=maria,
            cover_letter='Имею опыт анализа данных на Python, SQL и Power BI.',
            status=VacancyApplication.Status.ACCEPTED,
        )

        self.stdout.write(self.style.SUCCESS('Демонстрационные данные успешно созданы.'))

        self.stdout.write('')
        self.stdout.write('Тестовые пользователи:')
        self.stdout.write('Рекрутер 1: recruiter.it@example.com / DemoPassword123')
        self.stdout.write('Рекрутер 2: recruiter.hr@example.com / DemoPassword123')
        self.stdout.write('Соискатель: ivan.petrov@example.com / DemoPassword123')
        self.stdout.write('Соискатель: anna.smirnova@example.com / DemoPassword123')
        self.stdout.write('Соискатель: dmitry.sokolov@example.com / DemoPassword123')
        self.stdout.write('Соискатель: maria.kuznetsova@example.com / DemoPassword123')
        self.stdout.write('Соискатель: sergey.volkov@example.com / DemoPassword123')

    def create_user(self, email, password, role, first_name='', last_name=''):
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        return user