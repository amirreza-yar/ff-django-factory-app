from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class JobReferenceDraft(models.Model):
    client = models.OneToOneField(User, on_delete=models.CASCADE, related_name="draf_job_reference")

    code = models.PositiveIntegerField(null=True)
    project_name = models.CharField(max_length=50, null=True)

    class StateChoices(models.TextChoices):
        NSW = "NSW", "New South Wales"
        VIC = "VIC", "Victoria"
        QLD = "QLD", "Queensland"
        WA = "WA", "Western Australia"
        SA = "SA", "South Australia"
        TAS = "TAS", "Tasmania"
        ACT = "ACT", "Australian Capital Territory"
        NT = "NT", "Northern Territory"

    title = models.CharField(max_length=100, null=True)
    street_address = models.CharField(max_length=200, null=True)
    suburb = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=3, choices=StateChoices.choices, null=True)
    postcode = models.PositiveIntegerField(null=True)

    recipient_name = models.CharField(max_length=50, null=True)
    recipient_phone = models.CharField(max_length=50, null=True)