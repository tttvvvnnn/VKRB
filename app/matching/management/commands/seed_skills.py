from django.core.management.base import BaseCommand

from resumes.models import Skill

SKILLS = [
    # Языки программирования
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'C', 'Go',
    'Rust', 'PHP', 'Ruby', 'Swift', 'Kotlin', 'Scala', 'R', 'Dart',
    'Haskell', 'Elixir', 'Perl', 'Groovy', 'Lua', 'MATLAB', 'Objective-C',

    # Python-экосистема
    'Django', 'Flask', 'FastAPI', 'Celery', 'SQLAlchemy', 'Pydantic',
    'Pytest', 'Asyncio', 'Aiohttp',

    # JavaScript / Frontend
    'React', 'Vue.js', 'Angular', 'Next.js', 'Nuxt.js', 'Svelte',
    'jQuery', 'Redux', 'MobX', 'Webpack', 'Vite', 'Babel',

    # Backend-фреймворки
    'Spring', 'Spring Boot', 'ASP.NET', 'Express.js', 'NestJS',
    'Laravel', 'Symfony', 'Ruby on Rails', 'Gin', 'Echo',

    # Базы данных
    'PostgreSQL', 'MySQL', 'SQLite', 'MongoDB', 'Redis', 'Elasticsearch',
    'Cassandra', 'Oracle', 'MSSQL', 'ClickHouse', 'Firebase',
    'DynamoDB', 'Neo4j', 'InfluxDB',

    # Протоколы и стандарты
    'SQL', 'NoSQL', 'GraphQL', 'REST API', 'gRPC', 'WebSocket', 'ORM',
    'OAuth', 'JWT', 'SSL/TLS',

    # DevOps и инфраструктура
    'Docker', 'Docker Compose', 'Kubernetes', 'Helm', 'Terraform',
    'Ansible', 'CI/CD', 'Jenkins', 'GitLab CI', 'GitHub Actions',
    'CircleCI', 'Nginx', 'Apache', 'Bash', 'PowerShell', 'SSH',
    'Linux', 'RabbitMQ', 'Kafka',

    # Облако
    'AWS', 'GCP', 'Azure', 'Heroku', 'DigitalOcean', 'Vercel', 'Netlify',

    # Мониторинг
    'Prometheus', 'Grafana', 'ELK Stack', 'Sentry', 'Datadog', 'Zabbix',

    # Frontend-технологии
    'HTML', 'CSS', 'Sass', 'Bootstrap', 'Tailwind CSS', 'Material UI', 'Figma',

    # Тестирование — инструменты
    'Selenium', 'Playwright', 'Cypress', 'Jest', 'Mocha', 'JUnit',
    'Postman', 'JMeter', 'TestNG',

    # Методологии тестирования
    'TDD', 'BDD',
    'Ручное тестирование',
    'Автоматизированное тестирование',
    'Написание тест-кейсов',
    'Составление баг-репортов',
    'Нагрузочное тестирование',
    'Регрессионное тестирование',

    # Контроль версий и инструменты
    'Git', 'GitHub', 'GitLab', 'Bitbucket',
    'Jira', 'Confluence', 'Trello', 'Notion',

    # Методологии разработки
    'Agile', 'Scrum', 'Kanban',
    'SOLID', 'DDD', 'Clean Architecture',
    'Паттерны проектирования',
    'Микросервисная архитектура',
    'Событийно-ориентированная архитектура',
    'Код-ревью',

    # Data Science и ML
    'Pandas', 'NumPy', 'Scikit-learn', 'TensorFlow', 'PyTorch',
    'Keras', 'OpenCV', 'NLTK', 'spaCy', 'Matplotlib', 'Seaborn',
    'Plotly', 'Jupyter',
    'Машинное обучение',
    'Глубокое обучение',
    'Обработка естественного языка',
    'Компьютерное зрение',
    'Анализ данных',
    'Статистика',

    # BI и аналитика
    'Power BI', 'Tableau', 'Excel', 'Looker', 'Metabase', 'Apache Superset',

    # Мобильная разработка
    'React Native', 'Flutter', 'Xamarin',
    'Разработка под Android',
    'Разработка под iOS',

    # HR и управление
    'Подбор персонала',
    'Проведение интервью',
    'Адаптация персонала',
    'Управление проектами',
    'Тимлидерство',
    'Менторство',
    'Управление командой',
    'HR-аналитика',

    # Вёрстка и дизайн
    'Адаптивная вёрстка',
    'Кроссбраузерная вёрстка',
    'UX/UI-проектирование',

    # Общие профессиональные навыки
    'Администрирование Linux',
    'Информационная безопасность',
    'Документирование',
    'Технический английский',
    'Английский язык',
    'Написание технических заданий',
    'Работа с API',
    'Оптимизация запросов',
    'Профилирование и отладка',

    # Личностные и коммуникационные навыки
    'Коммуникабельность',
    'Работа в команде',
    'Самостоятельность',
    'Ответственность',
    'Обучаемость',
    'Многозадачность',
    'Внимательность к деталям',
    'Аналитическое мышление',
]


class Command(BaseCommand):
    help = 'Заполняет справочник навыков предустановленным списком.'

    def handle(self, *args, **options):
        created_count = 0

        for name in SKILLS:
            _, created = Skill.objects.get_or_create(name=name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Готово. Добавлено новых навыков: {created_count}. '
                f'Всего в базе: {Skill.objects.count()}.'
            )
        )