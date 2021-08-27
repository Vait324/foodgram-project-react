from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    email = models.EmailField(
        verbose_name='Email',
        help_text='Введите адрес эл.почты',
        unique=True
    )
    username = models.CharField(
        verbose_name='username',
        max_length=150,
        unique=True,
        help_text='Введите никнейм',
    )
    first_name = models.CharField('Имя', max_length=30)
    last_name = models.CharField('Фамилия', max_length=150)
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
