from django.contrib import admin

from .models import StoredFlashing, Order, JobReference, Address, Cart
from .sanpshots import (
    StoredFlashingSnapshot,
    PaymentSnapshot,
    MaterialSnapshot,
    JobReferenceSnapshot,
    SpecificationSnapshot,
)

admin.site.register(StoredFlashing)
admin.site.register(Order)
admin.site.register(JobReference)
admin.site.register(Address)
admin.site.register(Cart)


admin.site.register(StoredFlashingSnapshot)
admin.site.register(PaymentSnapshot)
admin.site.register(MaterialSnapshot)
admin.site.register(JobReferenceSnapshot)
admin.site.register(SpecificationSnapshot)