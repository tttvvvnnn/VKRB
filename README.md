# ВППП — Веб-приложение для подбора персонала

Платформа для автоматизированного подбора персонала с интеллектуальным сопоставлением резюме и вакансий на основе ИИ.

## Возможности

### Для соискателей
- Создание и управление резюме с выбором навыков из справочника
- Отклики на вакансии с сопроводительным письмом
- Автоматический подбор подходящих вакансий с оценкой релевантности
- Отслеживание статуса откликов

### Для рекрутеров
- Создание и управление вакансиями
- Просмотр входящих откликов и управление их статусами
- Автоматический подбор кандидатов под вакансию с ранжированием
- Доступ к публичным резюме кандидатов

### Интеллектуальное сопоставление
Алгоритм оценивает соответствие резюме и вакансии по четырём критериям:

| Критерий | Вес | Описание |
|----------|-----|---------|
| Навыки | 20% | Пересечение тегов навыков |
| Groq AI / TF-IDF | 50% | Семантический анализ (Llama 3.3 70B) или TF-IDF при отсутствии ключа |
| Опыт | 20% | Соответствие требуемому стажу |
| Город | 10% | Совпадение местоположения |

Результаты кэшируются в `MatchResult` и пересчитываются автоматически при изменении резюме или вакансии. При отсутствии `GROQ_API_KEY` система переключается на TF-IDF cosine similarity.

## Технологии

- **Backend:** Python 3.12, Django 5.2
- **База данных:** PostgreSQL
- **ИИ:** Groq API (Llama 3.3 70B), scikit-learn (TF-IDF)
- **Frontend:** Bootstrap 5, Tom Select
- **Инфраструктура:** Docker, Docker Compose, Nginx, Gunicorn
- **Тестирование:** pytest, pytest-django (48 тестов)

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/tttvvvnnn/VKRB.git
cd VKRB/main
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
```

Отредактировать `.env`:

```env
SECRET_KEY=ваш_секретный_ключ

POSTGRES_DB=vkrb
POSTGRES_USER=vkrb_user
POSTGRES_PASSWORD=ваш_пароль

GROQ_API_KEY=ваш_ключ_groq  # получить на console.groq.com
```

### 3. Запустить

```bash
docker compose up --build
```

При первом запуске автоматически выполнится:
- Применение миграций
- Загрузка справочника навыков (~130 штук)
- Создание суперпользователя `admin / Admin123!`
- Загрузка демонстрационных данных

### 4. Открыть в браузере

| URL | Описание |
|-----|---------|
| http://localhost | Основное приложение |
| http://localhost/admin | Административная панель |

## Тестирование

Проект покрыт **48 тестами**: 41 юнит-тест и 7 интеграционных.

### Запуск всех тестов

```bash
docker exec django-back bash -c "pytest accounts/tests.py resumes/tests.py vacancies/tests.py matching/tests.py tests_integration.py -v --tb=short"
```

### Запуск по модулям

```bash
# Юнит-тесты по модулям
docker exec django-back bash -c "pytest accounts/tests.py -v --tb=short"
docker exec django-back bash -c "pytest resumes/tests.py -v --tb=short"
docker exec django-back bash -c "pytest vacancies/tests.py -v --tb=short"
docker exec django-back bash -c "pytest matching/tests.py -v --tb=short"

# Интеграционные тесты
docker exec django-back bash -c "pytest tests_integration.py -v --tb=short"
```

### Покрытие тестами

| Модуль | Тесты | Что проверяется |
|--------|-------|----------------|
| `accounts/tests.py` | 8 | Регистрация, вход, создание Profile, декораторы ролей |
| `resumes/tests.py` | 9 | CRUD резюме, права доступа, видимость (public/hidden) |
| `vacancies/tests.py` | 7 | CRUD вакансий, отклики, избранное, уникальность MatchResult |
| `matching/tests.py` | 17 | Все функции сопоставления, кэш MatchResult, инвалидация |
| `tests_integration.py` | 7 | Сквозные сценарии: полный цикл соискателя и рекрутера, кэширование, ролевое разграничение |

### Интеграционные сценарии

- **Полный цикл соискателя** — регистрация → резюме → сопоставление (score > 0) → избранное → отклик
- **Полный цикл рекрутера** — регистрация → вакансия → ранжирование резюме → просмотр откликов → смена статуса (new → viewed → accepted)
- **Кэширование MatchResult** — кэш-хит при повторном вызове, инвалидация при изменении резюме и вакансии
- **Ролевое разграничение** — рекрутер заблокирован от действий соискателя, соискатель от рекрутерских, анонимный от всех защищённых URL

## Демонстрационные аккаунты

| Роль | Email | Пароль |
|------|-------|--------|
| Суперпользователь | admin | Admin123! |
| Рекрутер | recruiter.it@example.com | DemoPassword123 |
| Рекрутер | recruiter.hr@example.com | DemoPassword123 |
| Соискатель | ivan.petrov@example.com | DemoPassword123 |
| Соискатель | anna.smirnova@example.com | DemoPassword123 |
| Соискатель | dmitry.sokolov@example.com | DemoPassword123 |
| Соискатель | maria.kuznetsova@example.com | DemoPassword123 |

## Управление контейнерами

```bash
# Запустить
docker compose up --build

# Остановить (данные сохраняются)
docker compose down

# Полный сброс (удаляет БД и volumes)
docker compose down -v

# Просмотр логов
docker compose logs web --tail=50
```

## Структура проекта

```
app/
├── accounts/           # Пользователи и роли (соискатель / рекрутер)
├── resumes/            # Резюме и справочник навыков
├── vacancies/          # Вакансии и отклики
├── matching/           # Алгоритм сопоставления, кэш результатов
├── config/             # Настройки Django
├── templates/          # HTML-шаблоны
├── tests_integration.py  # Интеграционные тесты
└── pytest.ini          # Конфигурация pytest
```