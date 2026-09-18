from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, F, Value
from django.db.models.functions import Coalesce, Greatest
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse

from shop.models import Shop
from customers.models import Customer
from .models import Bill, BillItem, Prescription, Payment


# =========================================================
# CREATE NEW BILL
# =========================================================

@login_required
def new_bill(request):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    customers = shop.customers.all().order_by("name")

    if request.method == "POST":

        customer_id = request.POST.get("customer_id")

        try:
            customer = Customer.objects.get(
                id=customer_id,
                shop=shop
            )

        except (
            Customer.DoesNotExist,
            ValueError,
            TypeError
        ):
            return render(
                request,
                "billing/new_bill.html",
                {
                    "customers": customers,
                    "error": "Please select a valid customer."
                }
            )

        # -----------------------------------------------------
        # BILL ITEMS
        # -----------------------------------------------------

        item_names = request.POST.getlist("item_name[]")
        quantities = request.POST.getlist("quantity[]")
        rates = request.POST.getlist("rate[]")

        items = []
        subtotal = Decimal("0.00")

        for name, quantity, rate in zip(
            item_names,
            quantities,
            rates
        ):

            name = name.strip()

            if not name:
                continue

            try:
                quantity = int(quantity)
                rate = Decimal(rate)

            except (
                ValueError,
                InvalidOperation
            ):
                continue

            if quantity <= 0 or rate < 0:
                continue

            total = rate * quantity

            subtotal += total

            items.append({
                "name": name,
                "quantity": quantity,
                "rate": rate,
                "total": total,
            })

        if not items:
            return render(
                request,
                "billing/new_bill.html",
                {
                    "customers": customers,
                    "error": "Please add at least one bill item."
                }
            )

        # -----------------------------------------------------
        # PAYMENT
        # -----------------------------------------------------

        try:
            discount = Decimal(
                request.POST.get(
                    "discount",
                    "0"
                ) or "0"
            )

            advance_payment = Decimal(
                request.POST.get(
                    "advance_payment",
                    "0"
                ) or "0"
            )

        except InvalidOperation:

            discount = Decimal("0.00")
            advance_payment = Decimal("0.00")

        if discount < 0:
            discount = Decimal("0.00")

        if discount > subtotal:
            discount = subtotal

        grand_total = subtotal - discount

        if advance_payment < 0:
            advance_payment = Decimal("0.00")

        if advance_payment > grand_total:
            advance_payment = grand_total

        remaining_amount = grand_total - advance_payment

        # -----------------------------------------------------
        # PAYMENT METHOD
        # -----------------------------------------------------

        payment_method = request.POST.get(
            "payment_method",
            "cash"
        )

        valid_payment_methods = {
            "cash",
            "upi",
            "card",
            "other",
        }

        if payment_method not in valid_payment_methods:
            payment_method = "cash"

        # -----------------------------------------------------
        # DELIVERY / NOTES
        # -----------------------------------------------------

        delivery_date = request.POST.get(
            "delivery_date"
        ) or None

        notes = request.POST.get(
            "notes",
            ""
        ).strip()

        # -----------------------------------------------------
        # PRESCRIPTION
        # -----------------------------------------------------

        prescription_data = {

            "right_sph": request.POST.get(
                "right_sph",
                ""
            ).strip(),

            "right_cyl": request.POST.get(
                "right_cyl",
                ""
            ).strip(),

            "right_axis": request.POST.get(
                "right_axis",
                ""
            ).strip(),

            "right_add": request.POST.get(
                "right_add",
                ""
            ).strip(),

            "left_sph": request.POST.get(
                "left_sph",
                ""
            ).strip(),

            "left_cyl": request.POST.get(
                "left_cyl",
                ""
            ).strip(),

            "left_axis": request.POST.get(
                "left_axis",
                ""
            ).strip(),

            "left_add": request.POST.get(
                "left_add",
                ""
            ).strip(),

            "pd": request.POST.get(
                "pd",
                ""
            ).strip(),
        }

        # -----------------------------------------------------
        # CREATE EVERYTHING
        # -----------------------------------------------------

        with transaction.atomic():

            today = timezone.localdate()

            bill_count = Bill.objects.filter(
                shop=shop,
                bill_date__date=today
            ).count()

            bill_number = (
                f"{today.strftime('%Y%m%d')}-"
                f"{bill_count + 1:04d}"
            )

            while Bill.objects.filter(
                bill_number=bill_number
            ).exists():

                bill_count += 1

                bill_number = (
                    f"{today.strftime('%Y%m%d')}-"
                    f"{bill_count + 1:04d}"
                )

            bill = Bill.objects.create(
                shop=shop,
                customer=customer,
                bill_number=bill_number,
                subtotal=subtotal,
                discount=discount,
                grand_total=grand_total,
                advance_payment=advance_payment,
                remaining_amount=remaining_amount,
                payment_method=payment_method,
                delivery_date=delivery_date,
                notes=notes,
            )

            if advance_payment > 0:

                Payment.objects.create(
                    bill=bill,
                    amount=advance_payment,
                    payment_method=payment_method,
                    payment_date=bill.bill_date,
                )

            for item in items:

                BillItem.objects.create(
                    bill=bill,
                    item_name=item["name"],
                    quantity=item["quantity"],
                    rate=item["rate"],
                    total=item["total"],
                )

            Prescription.objects.create(
                bill=bill,
                **prescription_data
            )

        return redirect(
            f"{reverse('bill_detail', args=[bill.id])}?saved=1"
        )

    return render(
        request,
        "billing/new_bill.html",
        {
            "customers": customers,
        }
    )


# =========================================================
# BILL DETAILS
# =========================================================

@login_required
def bill_detail(request, bill_id):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    bill = get_object_or_404(
        Bill.objects
        .select_related(
            "customer",
            "shop"
        )
        .prefetch_related(
            "items",
            "payments"
        ),
        id=bill_id,
        shop=shop
    )

    try:
        prescription = bill.prescription
    except Prescription.DoesNotExist:
        prescription = None

    payments = list(
        bill.payments
        .all()
        .order_by(
            "payment_date",
            "id"
        )
    )

    for index, payment in enumerate(payments):

        if (
            bill.advance_payment > 0
            and index == 0
        ):
            payment.transaction_type = (
                "Initial / Advance Payment"
            )
        else:
            payment.transaction_type = (
                "Settlement Payment"
            )

    total_paid = sum(
        payment.amount
        for payment in payments
    ) or Decimal("0.00")

    calculated_remaining = max(
        bill.grand_total - total_paid,
        Decimal("0.00")
    )

    payment_count = len(payments)

    if calculated_remaining > 0:
        payment_status = "Pending"
    else:
        payment_status = "Paid"

    context = {
        "bill": bill,
        "prescription": prescription,
        "payment_status": payment_status,
        "payments": payments,
        "total_paid": total_paid,
        "calculated_remaining": calculated_remaining,
        "payment_count": payment_count,
    }

    return render(
        request,
        "billing/bill_detail.html",
        context
    )


# =========================================================
# EDIT BILL
# =========================================================

@login_required
def edit_bill(request, bill_id):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    bill = get_object_or_404(
        Bill.objects
        .select_related("customer", "shop")
        .prefetch_related("items", "payments"),
        id=bill_id,
        shop=shop
    )

    customers = shop.customers.all().order_by("name")

    try:
        prescription = bill.prescription
    except Prescription.DoesNotExist:
        prescription = None

    payments = list(
        bill.payments.all().order_by(
            "payment_date",
            "id"
        )
    )

    total_paid = sum(
        payment.amount
        for payment in payments
    ) or Decimal("0.00")

    if request.method == "POST":

        # -----------------------------------------------------
        # CUSTOMER
        # -----------------------------------------------------

        customer_id = request.POST.get("customer_id")

        try:
            customer = Customer.objects.get(
                id=customer_id,
                shop=shop
            )
        except (
            Customer.DoesNotExist,
            ValueError,
            TypeError
        ):
            return render(
                request,
                "billing/edit_bill.html",
                {
                    "bill": bill,
                    "customers": customers,
                    "prescription": prescription,
                    "error": "Please select a valid customer."
                }
            )

        # -----------------------------------------------------
        # ITEMS
        # -----------------------------------------------------

        item_names = request.POST.getlist("item_name[]")
        quantities = request.POST.getlist("quantity[]")
        rates = request.POST.getlist("rate[]")

        items = []
        subtotal = Decimal("0.00")

        for name, quantity, rate in zip(
            item_names,
            quantities,
            rates
        ):

            name = name.strip()

            if not name:
                continue

            try:
                quantity = int(quantity)
                rate = Decimal(rate)
            except (
                ValueError,
                InvalidOperation
            ):
                continue

            if quantity <= 0 or rate < 0:
                continue

            total = rate * quantity

            subtotal += total

            items.append({
                "name": name,
                "quantity": quantity,
                "rate": rate,
                "total": total,
            })

        if not items:
            return render(
                request,
                "billing/edit_bill.html",
                {
                    "bill": bill,
                    "customers": customers,
                    "prescription": prescription,
                    "error": "Please add at least one bill item."
                }
            )

        # -----------------------------------------------------
        # DISCOUNT
        # -----------------------------------------------------

        try:
            discount = Decimal(
                request.POST.get(
                    "discount",
                    "0"
                ) or "0"
            )
        except InvalidOperation:
            discount = Decimal("0.00")

        if discount < 0:
            discount = Decimal("0.00")

        if discount > subtotal:
            discount = subtotal

        grand_total = subtotal - discount

        # -----------------------------------------------------
        # IMPORTANT PAYMENT SAFETY
        # -----------------------------------------------------
        # Existing payment transactions are preserved.
        #
        # We don't allow the new bill total to become lower
        # than the amount already collected.
        # -----------------------------------------------------

        if grand_total < total_paid:

            return render(
                request,
                "billing/edit_bill.html",
                {
                    "bill": bill,
                    "customers": customers,
                    "prescription": prescription,
                    "error": (
                        f"Grand total cannot be less than "
                        f"₹{total_paid:.2f}, because that amount "
                        f"has already been collected."
                    ),
                }
            )

        # -----------------------------------------------------
        # PAYMENT METHOD
        # -----------------------------------------------------

        payment_method = request.POST.get(
            "payment_method",
            "cash"
        )

        valid_payment_methods = {
            "cash",
            "upi",
            "card",
            "other",
        }

        if payment_method not in valid_payment_methods:
            payment_method = "cash"

        # -----------------------------------------------------
        # DELIVERY / NOTES
        # -----------------------------------------------------

        delivery_date = request.POST.get(
            "delivery_date"
        ) or None

        notes = request.POST.get(
            "notes",
            ""
        ).strip()

        # -----------------------------------------------------
        # PRESCRIPTION
        # -----------------------------------------------------

        prescription_data = {

            "right_sph": request.POST.get(
                "right_sph",
                ""
            ).strip(),

            "right_cyl": request.POST.get(
                "right_cyl",
                ""
            ).strip(),

            "right_axis": request.POST.get(
                "right_axis",
                ""
            ).strip(),

            "right_add": request.POST.get(
                "right_add",
                ""
            ).strip(),

            "left_sph": request.POST.get(
                "left_sph",
                ""
            ).strip(),

            "left_cyl": request.POST.get(
                "left_cyl",
                ""
            ).strip(),

            "left_axis": request.POST.get(
                "left_axis",
                ""
            ).strip(),

            "left_add": request.POST.get(
                "left_add",
                ""
            ).strip(),

            "pd": request.POST.get(
                "pd",
                ""
            ).strip(),
        }

        remaining_amount = max(
            grand_total - total_paid,
            Decimal("0.00")
        )

        # -----------------------------------------------------
        # UPDATE
        # -----------------------------------------------------

        with transaction.atomic():

            bill.customer = customer
            bill.subtotal = subtotal
            bill.discount = discount
            bill.grand_total = grand_total
            bill.remaining_amount = remaining_amount
            bill.payment_method = payment_method
            bill.delivery_date = delivery_date
            bill.notes = notes

            # Keep the original advance amount.
            # Payment records remain untouched.
            bill.save(
                update_fields=[
                    "customer",
                    "subtotal",
                    "discount",
                    "grand_total",
                    "remaining_amount",
                    "payment_method",
                    "delivery_date",
                    "notes",
                ]
            )

            # -------------------------------------------------
            # REPLACE ITEMS
            # -------------------------------------------------

            bill.items.all().delete()

            for item in items:

                BillItem.objects.create(
                    bill=bill,
                    item_name=item["name"],
                    quantity=item["quantity"],
                    rate=item["rate"],
                    total=item["total"],
                )

            # -------------------------------------------------
            # PRESCRIPTION
            # -------------------------------------------------

            if prescription:

                for field, value in prescription_data.items():
                    setattr(
                        prescription,
                        field,
                        value
                    )

                prescription.save()

            else:

                Prescription.objects.create(
                    bill=bill,
                    **prescription_data
                )

        return redirect(
            f"{reverse('bill_detail', args=[bill.id])}?updated=1"
        )

    return render(
        request,
        "billing/edit_bill.html",
        {
            "bill": bill,
            "customers": customers,
            "prescription": prescription,
            "total_paid": total_paid,
        }
    )


# =========================================================
# DELETE BILL
# =========================================================

@login_required
def delete_bill(request, bill_id):

    if request.method != "POST":
        return redirect("bill_history")

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    bill = get_object_or_404(
        Bill,
        id=bill_id,
        shop=shop
    )

    with transaction.atomic():

        # BillItems, Prescription and Payments use
        # CASCADE and are deleted automatically.
        #
        # Customer is protected and remains in the system.
        bill.delete()

    return redirect(
        f"{reverse('bill_history')}?deleted=1"
    )


# =========================================================
# BILL HISTORY
# =========================================================

@login_required
def bill_history(request):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    bills = (
        shop.bills
        .select_related("customer")
        .prefetch_related("items", "payments")
        .annotate(
            total_paid=Sum("payments__amount")
        )
        .annotate(
            calculated_remaining=Greatest(
                F("grand_total") - Coalesce(
                    F("total_paid"),
                    Value(Decimal("0.00"))
                ),
                Value(Decimal("0.00")),
            )
        )
        .order_by("-bill_date")
    )

    query = request.GET.get(
        "q",
        ""
    ).strip()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    payment_method = request.GET.get(
        "payment_method",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if query:

        bills = bills.filter(
            Q(
                bill_number__icontains=query
            )
            |
            Q(
                customer__name__icontains=query
            )
            |
            Q(
                customer__mobile__icontains=query
            )
        )

    if date_from:

        bills = bills.filter(
            bill_date__date__gte=date_from
        )

    if date_to:

        bills = bills.filter(
            bill_date__date__lte=date_to
        )

    if payment_method in {
        "cash",
        "upi",
        "card",
        "other"
    }:

        bills = bills.filter(
            payment_method=payment_method
        )

    if status == "paid":

        bills = bills.filter(
            calculated_remaining=0
        )

    elif status == "pending":

        bills = bills.filter(
            calculated_remaining__gt=0
        )

    filtered_count = bills.count()

    filtered_total = (
        bills.aggregate(
            total=Sum("grand_total")
        )["total"]
        or 0
    )

    filtered_pending = (
        bills.aggregate(
            total=Sum("calculated_remaining")
        )["total"]
        or 0
    )

    paginator = Paginator(
        bills,
        12
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "billing/history.html",
        {
            "bills": page_obj,
            "page_obj": page_obj,
            "query": query,
            "date_from": date_from,
            "date_to": date_to,
            "payment_method": payment_method,
            "status": status,
            "filtered_count": filtered_count,
            "filtered_total": filtered_total,
            "filtered_pending": filtered_pending,
        },
    )


# =========================================================
# SETTLE / COLLECT PENDING PAYMENT
# =========================================================

@login_required
def settle_payment(request, bill_id):

    if request.method != "POST":
        return redirect("bill_history")

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    with transaction.atomic():

        bill = get_object_or_404(
            Bill.objects.select_for_update(),
            id=bill_id,
            shop=shop,
        )

        total_paid = (
            bill.payments.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        current_remaining = max(
            bill.grand_total - total_paid,
            Decimal("0.00")
        )

        if current_remaining <= 0:

            bill.remaining_amount = Decimal("0.00")

            bill.save(
                update_fields=[
                    "remaining_amount"
                ]
            )

            return redirect("bill_history")

        try:

            amount = Decimal(
                request.POST.get(
                    "amount",
                    "0"
                ) or "0"
            )

        except InvalidOperation:

            amount = Decimal("0.00")

        payment_method = request.POST.get(
            "payment_method",
            "cash"
        )

        valid_payment_methods = {
            "cash",
            "upi",
            "card",
            "other"
        }

        if payment_method not in valid_payment_methods:
            payment_method = "cash"

        if amount <= 0:
            return redirect("bill_history")

        if amount > current_remaining:
            return redirect("bill_history")

        Payment.objects.create(
            bill=bill,
            amount=amount,
            payment_method=payment_method,
        )

        bill.remaining_amount = (
            current_remaining - amount
        )

        bill.save(
            update_fields=[
                "remaining_amount"
            ]
        )

    return redirect(
        f"{reverse('bill_history')}?settled=1"
    )


# =========================================================
# SEND BILL TO WHATSAPP - FREE VERSION
# =========================================================

@login_required
def send_whatsapp(request, bill_id):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    bill = get_object_or_404(
        Bill.objects
        .select_related("customer", "shop")
        .prefetch_related("items", "payments"),
        id=bill_id,
        shop=shop
    )

    mobile = (bill.customer.mobile or "").strip()

    if not mobile:
        return redirect(
            "bill_detail",
            bill_id=bill.id
        )

    mobile = "".join(
        character
        for character in mobile
        if character.isdigit()
    )

    if len(mobile) == 10:
        mobile = "91" + mobile

    payments = list(
        bill.payments
        .all()
        .order_by("payment_date", "id")
    )

    total_paid = sum(
        payment.amount
        for payment in payments
    ) or Decimal("0.00")

    calculated_remaining = max(
        bill.grand_total - total_paid,
        Decimal("0.00")
    )

    payment_method = (
        bill.get_payment_method_display()
    )

    item_lines = []

    for item in bill.items.all():

        item_lines.append(
            f"• {item.item_name} × {item.quantity} - "
            f"₹{item.total:.2f}"
        )

    items_text = "\n".join(item_lines)

    delivery_text = ""

    if bill.delivery_date:

        delivery_text = (
            f"\nDelivery Date: "
            f"{bill.delivery_date.strftime('%d %b %Y')}"
        )

    message = (
        f"Hello {bill.customer.name} 👋\n\n"

        f"Thank you for visiting "
        f"{bill.shop.shop_name}.\n\n"

        f"*Bill Details*\n"
        f"Bill No: {bill.bill_number}\n"
        f"Bill Date: "
        f"{bill.bill_date.strftime('%d %b %Y')}\n\n"

        f"*Items*\n"
        f"{items_text}\n\n"

        f"Subtotal: ₹{bill.subtotal:.2f}\n"
        f"Discount: ₹{bill.discount:.2f}\n"
        f"*Grand Total: ₹{bill.grand_total:.2f}*\n\n"

        f"Paid: ₹{total_paid:.2f}\n"
        f"Remaining: ₹{calculated_remaining:.2f}\n"
        f"Payment Method: {payment_method}"
        f"{delivery_text}\n\n"

        f"Thank you for choosing "
        f"{bill.shop.shop_name}.\n"
        f"We appreciate your business. 🙏"
    )

    whatsapp_url = (
        f"https://wa.me/{mobile}"
        f"?text={quote(message)}"
    )

    return HttpResponseRedirect(
        whatsapp_url
    )


# =========================================================
# SETTINGS
# =========================================================

@login_required
def settings(request):

    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect("shop_setup")

    return render(
        request,
        "settings.html",
        {
            "shop": shop,
            "user": request.user,
        }
    )