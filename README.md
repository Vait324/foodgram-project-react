# Foodgram

FOODGRAM. Продуктовый помощник, который позволяет создавать рецепты и делиться ими. Также есть возможность добавлять избраные рецепты, создавать и скачивать список покупок.
## Технологии:
Python, Django, Docker

## Настройка проекта:
- Команды выполняются в директории infra
```
- docker-compose up -d
- docker-compose exec backend python manage.py migrate --noinput
- docker-compose exec backend python manage.py collectstatic --no-input
```
- Остановка проекта
```
- docker-compose stop
```
- Создание администратора
```
- docker-compose exec backend python manage.py createsuperuser
```
### Автор:
Павел В. Студент Яндекс.Практикум
