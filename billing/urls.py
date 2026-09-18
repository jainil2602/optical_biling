from django.urls import path

from . import views
from .payment_views import payment_history


urlpatterns = [

    # -----------------------------------------------------
    # NEW BILL
    # -----------------------------------------------------

    path(
        "new/",
        views.new_bill,
        name="new_bill"
    ),

    # -----------------------------------------------------
    # BILL HISTORY
    # -----------------------------------------------------

    path(
        "history/",
        views.bill_history,
        name="bill_history"
    ),

    # -----------------------------------------------------
    # PAYMENTS
    # -----------------------------------------------------

    path(
        "payments/",
        payment_history,
        name="payment_history"
    ),

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    path(
        "settings/",
        views.settings,
        name="settings"
    ),

    # -----------------------------------------------------
    # BILL EDIT
    # -----------------------------------------------------

    path(
        "<int:bill_id>/edit/",
        views.edit_bill,
        name="edit_bill"
    ),

    # -----------------------------------------------------
    # BILL DELETE
    # -----------------------------------------------------

    path(
        "<int:bill_id>/delete/",
        views.delete_bill,
        name="delete_bill"
    ),

    # -----------------------------------------------------
    # BILL PAYMENT SETTLEMENT
    # -----------------------------------------------------

    path(
        "<int:bill_id>/settle/",
        views.settle_payment,
        name="settle_payment"
    ),

    # -----------------------------------------------------
    # WHATSAPP
    # -----------------------------------------------------

    path(
        "<int:bill_id>/whatsapp/",
        views.send_whatsapp,
        name="send_whatsapp"
    ),

    # -----------------------------------------------------
    # BILL DETAILS
    # -----------------------------------------------------

    path(
        "<int:bill_id>/",
        views.bill_detail,
        name="bill_detail"
    ),
]