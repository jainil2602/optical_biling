from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from shop.models import Shop
from .models import Payment


@login_required
def payment_history(request):

    # =========================================================
    # SHOP
    # =========================================================

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    # =========================================================
    # FILTER VALUES
    # =========================================================

    period = request.GET.get(
        "period",
        "today"
    ).lower()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    payment_type = request.GET.get(
        "payment_type",
        ""
    ).lower()

    from_date = request.GET.get(
        "from_date",
        ""
    ).strip()

    to_date = request.GET.get(
        "to_date",
        ""
    ).strip()

    # =========================================================
    # PERIOD LABELS
    # =========================================================

    period_labels = {
        "today": "Today",
        "week": "This Week",
        "month": "This Month",
        "year": "This Year",
        "all": "All Time",
        "custom": "Custom Date",
    }

    if period not in period_labels:
        period = "today"

    today = timezone.localdate()

    # =========================================================
    # BASE PAYMENT QUERYSET
    # =========================================================

    payments = (
        Payment.objects
        .filter(
            bill__shop=shop
        )
        .select_related(
            "bill",
            "bill__customer"
        )
        .order_by(
            "-payment_date",
            "-id"
        )
    )

    # =========================================================
    # DATE FILTER
    # =========================================================

    if period == "today":

        payments = payments.filter(
            payment_date__date=today
        )

        range_text = today.strftime(
            "%d %b %Y"
        )

    elif period == "week":

        week_start = today - timedelta(
            days=today.weekday()
        )

        payments = payments.filter(
            payment_date__date__range=(
                week_start,
                today
            )
        )

        range_text = (
            f"{week_start.strftime('%d %b')} – "
            f"{today.strftime('%d %b %Y')}"
        )

    elif period == "month":

        month_start = today.replace(
            day=1
        )

        payments = payments.filter(
            payment_date__date__range=(
                month_start,
                today
            )
        )

        range_text = (
            f"{month_start.strftime('%d %b %Y')} – "
            f"{today.strftime('%d %b %Y')}"
        )

    elif period == "year":

        year_start = today.replace(
            month=1,
            day=1
        )

        payments = payments.filter(
            payment_date__date__range=(
                year_start,
                today
            )
        )

        range_text = (
            f"{year_start.strftime('%d %b %Y')} – "
            f"{today.strftime('%d %b %Y')}"
        )

    elif period == "custom":

        if from_date and to_date:

            if from_date <= to_date:

                payments = payments.filter(
                    payment_date__date__range=(
                        from_date,
                        to_date
                    )
                )

                range_text = (
                    f"{from_date} – {to_date}"
                )

            else:

                payments = payments.none()

                range_text = (
                    "Invalid date range"
                )

        elif from_date:

            payments = payments.filter(
                payment_date__date__gte=from_date
            )

            range_text = (
                f"From {from_date}"
            )

        elif to_date:

            payments = payments.filter(
                payment_date__date__lte=to_date
            )

            range_text = (
                f"Until {to_date}"
            )

        else:

            range_text = (
                "Select a date range"
            )

    else:

        range_text = (
            "All recorded payment transactions"
        )

    # =========================================================
    # PAYMENT TYPE FILTER
    # =========================================================

    valid_payment_types = {
        "cash",
        "upi",
        "card",
        "other",
    }

    if payment_type in valid_payment_types:

        payments = payments.filter(
            payment_method=payment_type
        )

    else:

        payment_type = ""

    # =========================================================
    # SEARCH FILTER
    # =========================================================

    if search:

        payments = payments.filter(
            Q(
                bill__customer__name__icontains=search
            )
            |
            Q(
                bill__customer__mobile__icontains=search
            )
            |
            Q(
                bill__bill_number__icontains=search
            )
        )

    # =========================================================
    # IMPORTANT:
    # CALCULATE EVERYTHING FROM THE FINAL QUERYSET
    # =========================================================

    cash_total = (
        payments
        .filter(
            payment_method="cash"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    upi_total = (
        payments
        .filter(
            payment_method="upi"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    card_total = (
        payments
        .filter(
            payment_method="card"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    other_total = (
        payments
        .filter(
            payment_method="other"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # GRAND PAYMENT TOTAL
    # =========================================================

    total_collected = (
        payments
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # TRANSACTION COUNT
    # =========================================================

    transaction_count = payments.count()

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # Payment records
        "payments": payments,

        # Date
        "period": period,
        "period_label": period_labels[period],
        "range_text": range_text,

        # Custom date
        "from_date": from_date,
        "to_date": to_date,

        # Search
        "search": search,

        # Payment type
        "payment_type": payment_type,

        # Totals
        "cash_total": cash_total,
        "upi_total": upi_total,
        "card_total": card_total,
        "other_total": other_total,
        "total_collected": total_collected,

        # Count
        "transaction_count": transaction_count,
    }

    return render(
        request,
        "billing/payments.html",
        context
    )