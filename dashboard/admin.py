from django.contrib import admin

from .models import StoredFlashing, Order

admin.site.register(StoredFlashing)
admin.site.register(Order)