from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, UserManager
from django.contrib.auth import get_user_model

class CustomUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        phone = extra_fields.get('phone')
        if phone is None:
            raise ValueError(_('The phone field must be set'))

        email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        # superusers need a phone too
        if extra_fields.get('phone') is None:
            raise ValueError(_('Superuser must have a phone number.'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    factory = models.ForeignKey(
        'factory.Factory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients"
    )

    objects = CustomUserManager()
    
    # phone = models.PositiveIntegerField()
    
    # is_phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"User {self.id} - {self.email}"