from django.contrib import admin
from .models import Bill, BillItem, Prescription, Payment

admin.site.register(Bill)
admin.site.register(BillItem)
admin.site.register(Prescription)
admin.site.register(Payment)
