from django.contrib import admin

from .models import StoredFlashing, Order, JobReference, Address

admin.site.register(StoredFlashing)
admin.site.register(Order)
admin.site.register(JobReference)
admin.site.register(Address)