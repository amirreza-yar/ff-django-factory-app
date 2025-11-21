import secrets
from allauth.account.adapter import DefaultAccountAdapter
from typing import Any
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from allauth.account import app_settings as allauth_account_settings
from allauth.account.adapter import get_adapter
from allauth.account.app_settings import EmailVerificationMethod
from allauth.account.models import EmailAddress, EmailConfirmation
from auth_kit.app_settings import auth_kit_settings
from auth_kit.utils import build_frontend_url, sensitive_post_parameters_m
from rest_framework.request import Request
from django.utils import timezone
from datetime import datetime
from allauth.account import app_settings
from auth_kit.views import VerifyEmailView
from rest_framework.response import Response
from django.http.response import Http404
from rest_framework import status


class CustomAccountAdapter(DefaultAccountAdapter):
    def generate_emailconfirmation_key(self, email):
        code_length = 6
        return secrets.randbelow(10**code_length - 1)

    def is_email_confirmed(self, email_confirmation):
        # Your custom expiration logic
        expiration_date = email_confirmation.sent + datetime.timedelta(seconds=5)

        print(
            "\n\nchecking for key expiration in fast email conf\n",
            expiration_date,
            timezone.now(),
            sep="\n",
        )

        return timezone.now() <= expiration_date


def send_verify_email(request: Request, user: AbstractUser) -> None:
    email_template = "account/email/email_confirmation_signup"

    email_address = EmailAddress.objects.get_for_user(user, user.email)

    model = EmailConfirmation
    emailconfirmation = model.create(email_address)
    emailconfirmation.sent = timezone.now()
    emailconfirmation.save()
    adapter = get_adapter()

    ctx: dict[str, Any] = {
        "user": user,
        "key": emailconfirmation.key,
        "activate_url": auth_kit_settings.GET_EMAIL_VERIFICATION_URL_FUNC(
            request, emailconfirmation
        ),
    }
    adapter.send_mail(email_template, emailconfirmation.email_address.email, ctx)
