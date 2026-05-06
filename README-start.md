# Старт Django-проекта через Docker

## 1. Открыть терминал в папке проекта

```powershell
cd hr_recruitment
```

## 2. Собрать Docker-образ

```powershell
docker compose build
```

## 3. Создать Django-проект внутри папки app

```powershell
docker compose run --rm web django-admin startproject config .
```

## 4. Создать приложения

```powershell
docker compose run --rm web python manage.py startapp accounts
docker compose run --rm web python manage.py startapp resumes
docker compose run --rm web python manage.py startapp vacancies
docker compose run --rm web python manage.py startapp matching
```

## 5. Выполнить миграции

```powershell
docker compose run --rm web python manage.py migrate
```

## 6. Создать администратора

```powershell
docker compose run --rm web python manage.py createsuperuser
```

## 7. Запустить сайт

```powershell
docker compose up
```

Сайт: http://127.0.0.1:8000/

Админка: http://127.0.0.1:8000/admin/
