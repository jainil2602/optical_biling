from django.db import models
from django.utils import timezone

from shop.models import Shop
from customers.models import Customer


class Bill(models.Model):

    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("card", "Card"),
        ("other", "Other"),
    ]

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="bills"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="bills"
    )

    bill_number = models.CharField(
        max_length=50,
        unique=True
    )

    bill_date = models.DateTimeField(
        auto_now_add=True
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    advance_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="cash"
    )

    delivery_date = models.DateField(
        blank=True,
        null=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.bill_number


class BillItem(models.Model):

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item_name = models.CharField(
        max_length=150
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.item_name} - {self.bill.bill_number}"


class Prescription(models.Model):

    bill = models.OneToOneField(
        Bill,
        on_delete=models.CASCADE,
        related_name="prescription"
    )

    right_sph = models.CharField(
        max_length=20,
        blank=True
    )

    right_cyl = models.CharField(
        max_length=20,
        blank=True
    )

    right_axis = models.CharField(
        max_length=20,
        blank=True
    )

    right_add = models.CharField(
        max_length=20,
        blank=True
    )

    left_sph = models.CharField(
        max_length=20,
        blank=True
    )

    left_cyl = models.CharField(
        max_length=20,
        blank=True
    )

    left_axis = models.CharField(
        max_length=20,
        blank=True
    )

    left_add = models.CharField(
        max_length=20,
        blank=True
    )

    pd = models.CharField(
        max_length=20,
        blank=True
    )

    def __str__(self):
        return f"Prescription - {self.bill.bill_number}"


class Payment(models.Model):

    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("card", "Card"),
        ("other", "Other"),
    ]

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="cash"
    )

    # IMPORTANT:
    # Do NOT use auto_now_add here.
    #
    # Initial advance payment will explicitly use bill.bill_date.
    # Later settlement payments will automatically use the
    # actual current date/time.
    payment_date = models.DateTimeField(
        default=timezone.now
    )

    notes = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.bill.bill_number} - ₹{self.amount}"