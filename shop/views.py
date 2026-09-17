from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ShopForm


@login_required
def shop_setup(request):
    shop = getattr(request.user, "shop", None)

    if request.method == "POST":
        form = ShopForm(request.POST, request.FILES, instance=shop)

        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user
            shop.save()

            return redirect("dashboard")

    else:
        form = ShopForm(instance=shop)

    return render(
        request,
        "shop/setup.html",
        {"form": form}
    )