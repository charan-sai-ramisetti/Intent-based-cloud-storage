from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """
    Minimal custom user model.
    Uses Django's built-in auth features safely.
    """

    email = models.EmailField(unique=True)

    # Email verification (minimal setup)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        null=True,
        blank=True
    )

    reset_password_token = models.UUIDField(
    null=True,
    blank=True,
    unique=True
    )
    reset_password_expiry = models.DateTimeField(
        null=True,
        blank=True
    )


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
