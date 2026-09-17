from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from shop.models import Shop
from billing.models import BillItem


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.user.is_authenticated:

        try:
            request.user.shop
            return redirect("dashboard")

        except Shop.DoesNotExist:
            return redirect("shop_setup")

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            try:
                user.shop
                return redirect("dashboard")

            except Shop.DoesNotExist:
                return redirect("shop_setup")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid username or password."
            }
        )

    return render(
        request,
        "accounts/login.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@login_required
def dashboard(request):

    # -----------------------------------------------------
    # GET SHOP
    # -----------------------------------------------------

    try:
        shop = request.user.shop

    except Shop.DoesNotExist:
        return redirect("shop_setup")


    # -----------------------------------------------------
    # BASIC COUNTS
    # -----------------------------------------------------

    total_bills = shop.bills.count()

    total_customers = shop.customers.count()


    # -----------------------------------------------------
    # PENDING AMOUNT
    # -----------------------------------------------------

    pending_amount = (
        shop.bills
        .aggregate(
            total=Sum("remaining_amount")
        )["total"] or 0
    )


    # -----------------------------------------------------
    # TODAY
    # -----------------------------------------------------

    today = timezone.localdate()


    # -----------------------------------------------------
    # TODAY'S SALES
    # -----------------------------------------------------

    todays_sales = (
        shop.bills
        .filter(
            bill_date__date=today
        )
        .aggregate(
            total=Sum("grand_total")
        )["total"] or 0
    )


    # -----------------------------------------------------
    # CURRENT MONTH
    # -----------------------------------------------------

    month_start = today.replace(day=1)


    # -----------------------------------------------------
    # NEXT MONTH
    # Used only to determine current month's end.
    # -----------------------------------------------------

    if today.month == 12:

        next_month = today.replace(
            year=today.year + 1,
            month=1,
            day=1
        )

    else:

        next_month = today.replace(
            month=today.month + 1,
            day=1
        )


    month_end = next_month - timedelta(days=1)


    # -----------------------------------------------------
    # CURRENT MONTH BILLS
    # -----------------------------------------------------

    current_month_bills = (
        shop.bills
        .filter(
            bill_date__date__range=(
                month_start,
                month_end
            )
        )
    )


    # -----------------------------------------------------
    # CURRENT MONTH SALES
    # -----------------------------------------------------

    monthly_sales = (
        current_month_bills
        .aggregate(
            total=Sum("grand_total")
        )["total"] or 0
    )


    # =====================================================
    # SALES OVERVIEW CHART
    # =====================================================

    # Get actual sales grouped by date.
    daily_sales_rows = (
        current_month_bills
        .annotate(
            sale_day=TruncDate("bill_date")
        )
        .values("sale_day")
        .annotate(
            total=Sum("grand_total")
        )
        .order_by("sale_day")
    )


    # Convert database result into:
    #
    # {
    #     date: total_sales
    # }
    #

    daily_sales_map = {}

    for row in daily_sales_rows:

        if row["sale_day"]:

            daily_sales_map[
                row["sale_day"]
            ] = float(row["total"] or 0)


    # -----------------------------------------------------
    # Create labels for every day of current month.
    # -----------------------------------------------------

    sales_chart_labels = []

    sales_chart_values = []


    current_day = month_start


    while current_day <= today:

        sales_chart_labels.append(
            current_day.strftime("%d %b")
        )

        sales_chart_values.append(
            daily_sales_map.get(
                current_day,
                0
            )
        )

        current_day += timedelta(days=1)


    # =====================================================
    # RECENT BILLS
    # =====================================================

    recent_bills = (
        shop.bills
        .select_related("customer")
        .order_by("-bill_date")[:8]
    )


    # =====================================================
    # TOP SELLING ITEMS
    # =====================================================

    top_items_queryset = (
        BillItem.objects
        .filter(
            bill__shop=shop,
            bill__bill_date__date__range=(
                month_start,
                month_end
            )
        )
        .values("item_name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_sales=Sum("total")
        )
        .order_by("-total_quantity")[:5]
    )


    top_items = list(top_items_queryset)


    # -----------------------------------------------------
    # Find highest quantity.
    # Used for progress bar.
    # -----------------------------------------------------

    top_item_max = 0


    if top_items:

        top_item_max = (
            top_items[0]["total_quantity"] or 0
        )


    # -----------------------------------------------------
    # Prepare items for template.
    # -----------------------------------------------------

    top_items_data = []


    for item in top_items:

        quantity = (
            item["total_quantity"] or 0
        )


        sales = (
            item["total_sales"] or 0
        )


        if top_item_max > 0:

            percentage = int(
                (quantity / top_item_max) * 100
            )

        else:

            percentage = 0


        top_items_data.append(
            {
                "name": item["item_name"],
                "quantity": quantity,
                "sales": sales,
                "percentage": percentage,
            }
        )


    # =====================================================
    # DASHBOARD CONTEXT
    # =====================================================

    context = {

        # KPI
        "total_bills":
            total_bills,

        "total_customers":
            total_customers,

        "pending_amount":
            pending_amount,

        "todays_sales":
            todays_sales,


        # Sales Overview
        "monthly_sales":
            monthly_sales,

        "sales_chart_labels":
            sales_chart_labels,

        "sales_chart_values":
            sales_chart_values,


        # Recent Bills
        "recent_bills":
            recent_bills,


        # Top Selling Items
        "top_items":
            top_items_data,
    }


    return render(
        request,
        "dashboard.html",
        context
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    logout(request)

    return redirect("login")