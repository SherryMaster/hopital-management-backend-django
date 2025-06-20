# Generated by Django 5.2.3 on 2025-06-19 14:57

import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentGateway",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "gateway_type",
                    models.CharField(
                        choices=[
                            ("stripe", "Stripe"),
                            ("paypal", "PayPal"),
                            ("square", "Square"),
                            ("authorize_net", "Authorize.Net"),
                            ("braintree", "Braintree"),
                            ("mock", "Mock Gateway (Testing)"),
                        ],
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("is_test_mode", models.BooleanField(default=True)),
                (
                    "api_configuration",
                    models.JSONField(
                        default=dict, help_text="Gateway-specific API configuration"
                    ),
                ),
                ("supports_credit_cards", models.BooleanField(default=True)),
                ("supports_debit_cards", models.BooleanField(default=True)),
                ("supports_bank_transfers", models.BooleanField(default=False)),
                ("supports_digital_wallets", models.BooleanField(default=False)),
                (
                    "transaction_fee_percentage",
                    models.DecimalField(
                        decimal_places=4, default=Decimal("0.0290"), max_digits=5
                    ),
                ),
                (
                    "transaction_fee_fixed",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.30"), max_digits=10
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PaymentMethod",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "payment_type",
                    models.CharField(
                        choices=[
                            ("credit_card", "Credit Card"),
                            ("debit_card", "Debit Card"),
                            ("bank_account", "Bank Account"),
                            ("digital_wallet", "Digital Wallet"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "gateway_payment_method_id",
                    models.CharField(
                        help_text="Gateway-specific payment method ID", max_length=200
                    ),
                ),
                (
                    "display_name",
                    models.CharField(
                        help_text="e.g., 'Visa ending in 1234'", max_length=100
                    ),
                ),
                ("last_four_digits", models.CharField(blank=True, max_length=4)),
                ("expiry_month", models.IntegerField(blank=True, null=True)),
                ("expiry_year", models.IntegerField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "gateway",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="billing.paymentgateway",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_methods",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_default", "-created_at"],
                "unique_together": {("patient", "gateway_payment_method_id")},
            },
        ),
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                            ("requires_action", "Requires Action"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "gateway_transaction_id",
                    models.CharField(blank=True, max_length=200),
                ),
                (
                    "gateway_response",
                    models.JSONField(default=dict, help_text="Full gateway response"),
                ),
                ("error_code", models.CharField(blank=True, max_length=100)),
                ("error_message", models.TextField(blank=True)),
                (
                    "attempted_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="billing.payment",
                    ),
                ),
                (
                    "gateway",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="billing.paymentgateway",
                    ),
                ),
                (
                    "payment_method",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="billing.paymentmethod",
                    ),
                ),
            ],
            options={
                "ordering": ["-attempted_at"],
            },
        ),
    ]
