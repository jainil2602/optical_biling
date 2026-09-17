from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


def create_initial_payments(apps, schema_editor):
    Bill = apps.get_model("billing", "Bill")
    Payment = apps.get_model("billing", "Payment")

    for bill in Bill.objects.all().iterator():
        amount = bill.advance_payment or Decimal("0.00")
        if amount > 0:
            Payment.objects.create(
                bill=bill,
                amount=amount,
                payment_method=bill.payment_method or "cash",
            )


def reverse_initial_payments(apps, schema_editor):
    Payment = apps.get_model("billing", "Payment")
    Payment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("payment_method", models.CharField(choices=[("cash", "Cash"), ("upi", "UPI"), ("card", "Card"), ("other", "Other")], default="cash", max_length=20)),
                ("payment_date", models.DateTimeField(auto_now_add=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="billing.bill")),
            ],
        ),
        migrations.RunPython(create_initial_payments, reverse_initial_payments),
    ]
