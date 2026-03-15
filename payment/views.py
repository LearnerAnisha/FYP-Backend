import logging
import requests as http_requests

from django.conf import settings
from django.shortcuts import redirect as django_redirect          # ← NEW
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Payment
from rest_framework.permissions import AllowAny
from .serializers import PaymentInitSerializer, PaymentSerializer
from .exceptions import (
    ValidationError,
    PaymentNotFoundError,
    PaymentAlreadyProcessedError,
    MissingCallbackDataError,
    InvalidCallbackDataError,
    SignatureMismatchError,
    TransactionNotFoundError,
    EsewaAPITimeoutError,
    EsewaAPIUnreachableError,
    EsewaAPIError,
)
from .utils import (
    generate_esewa_signature,
    verify_esewa_signature,
    decode_esewa_response,
    verify_payment_with_esewa,
)

logger = logging.getLogger(__name__)


# ─── 1. INITIATE PAYMENT ─────────────────────────────────────────────────────

class InitiatePaymentView(APIView):
    """
    POST /api/payments/initiate/

    Validates payment data, creates a Payment record (PENDING),
    generates HMAC signature, and returns the eSewa form payload.

    Request Body:
        {
            "amount": 499,
            "tax_amount": 0,       (optional, default 0)
            "service_charge": 0,   (optional, default 0)
            "delivery_charge": 0   (optional, default 0)
        }

    Response 201:
        {
            "message": "Payment initiated successfully.",
            "payment_id": 1,
            "transaction_uuid": "550e8400-...",
            "esewa_url": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
            "esewa_payload": { ... },
            "instructions": "Submit esewa_payload as a POST form to esewa_url."
        }
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PaymentInitSerializer(data=request.data)

        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid payment data. Please check the fields below.",
                details=serializer.errors,
            )

        data = serializer.validated_data

        # Create PENDING payment record
        payment = Payment.objects.create(
            amount          = data["amount"],
            tax_amount      = data.get("tax_amount",      0),
            service_charge  = data.get("service_charge",  0),
            delivery_charge = data.get("delivery_charge", 0),
            total_amount    = data["total_amount"],
            status          = Payment.Status.PENDING,
        )

        logger.info(
            "Payment created | id=%s | uuid=%s | total=NPR %s",
            payment.pk, payment.transaction_uuid, payment.total_amount,
        )

        # Generate HMAC-SHA256 signature
        signature = generate_esewa_signature(
            total_amount     = str(payment.total_amount),
            transaction_uuid = str(payment.transaction_uuid),
            product_code     = settings.ESEWA_PRODUCT_CODE,
        )

        esewa_payload = {
            "amount"                  : str(payment.amount),
            "tax_amount"              : str(payment.tax_amount),
            "service_charge"          : str(payment.service_charge),
            "delivery_charge"         : str(payment.delivery_charge),
            "total_amount"            : str(payment.total_amount),
            "transaction_uuid"        : str(payment.transaction_uuid),
            "product_code"            : settings.ESEWA_PRODUCT_CODE,
            "product_service_charge"  : str(payment.service_charge),
            "product_delivery_charge" : str(payment.delivery_charge),
            # DRF handles these URLs — after verifying, DRF redirects to FRONTEND_URL
            "success_url"             : f"{settings.DOMAIN}/api/payment/success/",
            "failure_url"             : f"{settings.DOMAIN}/api/payment/failure/",
            "signed_field_names"      : "total_amount,transaction_uuid,product_code",
            "signature"               : signature,
        }

        return Response(
            {
                "message"         : "Payment initiated successfully.",
                "payment_id"      : payment.pk,
                "transaction_uuid": str(payment.transaction_uuid),
                "esewa_url"       : f"{settings.ESEWA_BASE_URL}/api/epay/main/v2/form",
                "esewa_payload"   : esewa_payload,
                "instructions"    : "Submit esewa_payload as a POST HTML form to esewa_url.",
            },
            status=status.HTTP_201_CREATED,
        )


# ─── 2. SUCCESS CALLBACK ──────────────────────────────────────────────────────

class PaymentSuccessView(APIView):
    """
    GET /api/payments/success/?data=<base64_encoded_json>

    Called by eSewa after a successful payment.

    Steps:
        1. Decode base64 data
        2. Verify HMAC signature
        3. Lookup Payment in DB
        4. Verify with eSewa status API (server-to-server)
        5. Mark payment COMPLETE
        6. Redirect browser to frontend /payment/callback?status=success
    """
    permission_classes = [AllowAny]
    def get(self, request):
        encoded_data = request.query_params.get("data")

        # Step 1: data param must be present
        if not encoded_data:
            raise MissingCallbackDataError()

        # Step 2: Decode base64 JSON
        try:
            esewa_data = decode_esewa_response(encoded_data)
        except ValueError as e:
            raise InvalidCallbackDataError(message=str(e))

        logger.info("eSewa success callback | data=%s", esewa_data)

        # Step 3: Verify HMAC signature
        signed_fields = esewa_data.get("signed_field_names", "").split(",")
        
        data_string = ",".join(
            f"{field}={esewa_data.get(field, '')}"
            for field in signed_fields
        )
        
        is_valid = verify_esewa_signature(
            data_string=data_string,
            received_signature=esewa_data.get("signature", "")
     )
        if not is_valid:
            raise SignatureMismatchError()

        # Step 4: Lookup payment in DB
        transaction_uuid = esewa_data.get("transaction_uuid")
        try:
            payment = Payment.objects.get(transaction_uuid=transaction_uuid)
        except Payment.DoesNotExist:
            raise TransactionNotFoundError(
                message=f"No payment found with transaction_uuid={transaction_uuid}."
            )

        # Guard: already processed
        if payment.status == Payment.Status.COMPLETE:
            frontend_url = f"{settings.FRONTEND_URL}/payment/callback?status=success"
            return django_redirect(frontend_url)

        # Step 5: Verify with eSewa server-to-server
        try:
            verify_response = verify_payment_with_esewa(
                transaction_uuid = str(payment.transaction_uuid),
                total_amount     = str(payment.total_amount),
            )
        except http_requests.Timeout:
            raise EsewaAPITimeoutError()
        except http_requests.ConnectionError:
            raise EsewaAPIUnreachableError()
        except http_requests.RequestException as e:
            raise EsewaAPIError(message=str(e))

        # Step 6: Check eSewa's returned status
        esewa_status = verify_response.get("status")
        if esewa_status != "COMPLETE":
            payment.status             = Payment.Status.FAILED
            payment.esewa_raw_response = verify_response
            payment.save(update_fields=["status", "esewa_raw_response", "updated_at"])

            logger.warning(
                "eSewa returned non-COMPLETE status=%s | txn=%s",
                esewa_status, transaction_uuid,
            )
            # ← Redirect browser to frontend failure page
            frontend_url = f"{settings.FRONTEND_URL}/payment/callback?status=failed"
            return django_redirect(frontend_url)

        # Step 7: Mark COMPLETE ✅
        payment.status             = Payment.Status.COMPLETE
        payment.esewa_ref_id       = verify_response.get("ref_id")
        payment.esewa_raw_response = verify_response
        payment.save(update_fields=["status", "esewa_ref_id", "esewa_raw_response", "updated_at"])

        logger.info("Payment COMPLETE | id=%s | ref_id=%s", payment.pk, payment.esewa_ref_id)

        # ← Redirect browser to frontend success page
        frontend_url = f"{settings.FRONTEND_URL}/payment/callback?status=success"
        return django_redirect(frontend_url)


# ─── 3. FAILURE CALLBACK ──────────────────────────────────────────────────────

class PaymentFailureView(APIView):
    """
    GET /api/payments/failure/?transaction_uuid=<uuid>

    Called by eSewa when the user cancels or payment fails.
    Marks the payment FAILED, then redirects browser to frontend.
    """
    permission_classes = [AllowAny] 
    def get(self, request):
        transaction_uuid = request.query_params.get("transaction_uuid")

        if not transaction_uuid:
            # eSewa may not always send uuid on failure
            frontend_url = f"{settings.FRONTEND_URL}/payment/callback?status=failed"
            return django_redirect(frontend_url)

        try:
            payment = Payment.objects.get(transaction_uuid=transaction_uuid)
        except Payment.DoesNotExist:
            # No record found — still redirect gracefully
            frontend_url = (
                f"{settings.FRONTEND_URL}/payment/callback"
                f"?status=failed&uuid={transaction_uuid}"
            )
            return django_redirect(frontend_url)

        if payment.status == Payment.Status.PENDING:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            logger.info("Payment marked FAILED | id=%s | uuid=%s", payment.pk, transaction_uuid)

        # ← Redirect browser to frontend failure page
        frontend_url = (
            f"{settings.FRONTEND_URL}/payment/callback"
            f"?status=failed&uuid={transaction_uuid}"
        )
        return django_redirect(frontend_url)


# ─── 4. PAYMENT STATUS ────────────────────────────────────────────────────────

class PaymentStatusView(APIView):
    """
    GET /api/payments/<payment_id>/status/

    Polled by PaymentCallback.jsx after eSewa redirects back.

    Response:
        { "payment": { id, status, esewa_ref_id, total_amount, ... } }
    """
    permission_classes = [AllowAny] 
    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            raise PaymentNotFoundError(
                message=f"Payment with ID {payment_id} does not exist."
            )

        return Response(
            {"payment": PaymentSerializer(payment).data},
            status=status.HTTP_200_OK,
        )


# ─── 5. PAYMENT LIST ─────────────────────────────────────────────────────────

class PaymentListView(APIView):
    """
    GET /api/payments/

    Returns all payment records.
    In production: filter by request.user and add authentication.

    Response:
        { "count": 5, "payments": [ ... ] }
    """
    permission_classes = [AllowAny] 
    def get(self, request):
        payments   = Payment.objects.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(
            {
                "count"   : payments.count(),
                "payments": serializer.data,
            },
            status=status.HTTP_200_OK,
        )