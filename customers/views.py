from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect

from shop.models import Shop
from .models import Customer


@login_required
def customer_add(request):

    try:
        shop = request.user.shop

    except Shop.DoesNotExist:
        return redirect("shop_setup")


    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        mobile = request.POST.get(
            "mobile",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()


        if not name or not mobile:

            return render(
                request,
                "customers/add.html",
                {
                    "error":
                    "Customer name and mobile number are required."
                }
            )


        Customer.objects.create(

            shop=shop,

            name=name,

            mobile=mobile,

            email=email,

            address=address,

        )


        return redirect("new_bill")


    return render(
        request,
        "customers/add.html"
    )


# ============================================================
# CUSTOMER LIST
# ============================================================

@login_required
def customer_list(request):

    try:

        shop = request.user.shop

    except Shop.DoesNotExist:

        return redirect("shop_setup")


    query = request.GET.get(
        "q",
        ""
    ).strip()


    customers = (
        shop.customers
        .all()
        .order_by("-created_at")
    )


    if query:

        customers = customers.filter(

            Q(name__icontains=query) |

            Q(mobile__icontains=query) |

            Q(email__icontains=query)

        )


    context = {

        "customers":
            customers,

        "query":
            query,

        "total_customers":
            shop.customers.count(),

    }


    return render(

        request,

        "customers/list.html",

        context

    )


# ============================================================
# CUSTOMER DETAIL
# ============================================================

@login_required
def customer_detail(
    request,
    customer_id
):

    try:

        shop = request.user.shop

    except Shop.DoesNotExist:

        return redirect("shop_setup")


    try:

        customer = Customer.objects.get(

            id=customer_id,

            shop=shop

        )

    except Customer.DoesNotExist:

        return redirect("customer_list")


    bills = (

        customer.bills

        .select_related("shop")

        .prefetch_related(
            "items",
            "prescription"
        )

        .order_by("-bill_date")

    )


    total_purchases = sum(

        bill.grand_total

        for bill in bills

    )


    pending_amount = sum(

        bill.remaining_amount

        for bill in bills

    )


    total_bills = bills.count()


    context = {

        "customer":
            customer,

        "bills":
            bills,

        "total_bills":
            total_bills,

        "total_purchases":
            total_purchases,

        "pending_amount":
            pending_amount,

    }


    return render(

        request,

        "customers/detail.html",

        context

    )