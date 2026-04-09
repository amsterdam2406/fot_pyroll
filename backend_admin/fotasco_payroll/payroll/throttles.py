from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------

class LoginThrottle(AnonRateThrottle):
    """
    Throttle unauthenticated login attempts by IP.
    Use AnonRateThrottle (IP-based) instead of UserRateThrottle so that
    brute-force attempts before a valid login are still caught.
    Rate: 5 attempts per minute — tight enough to block brute force,
    loose enough for a legitimate user who misremembers their password.
    Configured in settings:
        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_RATES': {
                'anon': '5/min',
                ...
            }
        }
    """
    scope = 'login'
    rate = '5/min'


# ---------------------------------------------------------------------------
# ATTENDANCE
# ---------------------------------------------------------------------------

class AttendanceThrottle(UserRateThrottle):
    """
    Throttle clock-in / clock-out actions per authenticated user.
    A legitimate employee clocks in and out at most twice a day, so
    10/min is generous for normal use while stopping runaway requests.
    Configured in settings:
        'attendance': '10/min'
    """
    scope = 'attendance'
    rate = '10/min'


# ---------------------------------------------------------------------------
# PAYMENT
# ---------------------------------------------------------------------------

class PaymentThrottle(UserRateThrottle):
    """
    Throttle payment initiation per authenticated user.
    Paystack charges per transaction; accidental or malicious loops are costly.
    20/hour is ample for a payroll admin running bulk payments while
    preventing abuse.
    Configured in settings:
        'payment': '20/hour'
    """
    scope = 'payment'
    rate = '20/hour'


# ---------------------------------------------------------------------------
# REGISTRATION  ← new
# ---------------------------------------------------------------------------

class RegisterThrottle(UserRateThrottle):
    """
    Throttle account creation per authenticated admin.
    An admin adding employees one-by-one rarely needs more than
    30 per hour; this prevents a compromised admin account from
    mass-creating users.
    Configured in settings:
        'register': '30/hour'
    """
    scope = 'register'
    rate = '30/hour'


# ---------------------------------------------------------------------------
# PASSWORD VERIFICATION  ← new
# ---------------------------------------------------------------------------

class VerifyPasswordThrottle(UserRateThrottle):
    """
    Throttle the /verify-password/ endpoint.
    This endpoint gates sensitive exports; limit retries to slow
    any attempt to enumerate passwords through the API.
    Configured in settings:
        'verify_password': '5/min'
    """
    scope = 'verify_password'
    rate = '5/min'


# ---------------------------------------------------------------------------
# OTP / RESEND OTP  ← new
# ---------------------------------------------------------------------------

class OTPThrottle(UserRateThrottle):
    """
    Throttle OTP verification and resend attempts per user.
    3 OTP resends per 10 minutes prevents SMS/email flooding and
    OTP brute-force (6-digit code = 1 000 000 possibilities; at
    3 attempts/min an attacker would need ~231 days — infeasible).
    Configured in settings:
        'otp': '3/10min'   or   '10/hour'
    """
    scope = 'otp'
    rate = '10/hour'


# ---------------------------------------------------------------------------
# EXPORT TOKEN REQUEST  ← new
# ---------------------------------------------------------------------------

class ExportTokenThrottle(UserRateThrottle):
    """
    Throttle export-token generation per admin user.
    Tokens grant temporary access to bulk CSV exports; generating
    too many in quick succession indicates abuse or a scripting attack.
    Configured in settings:
        'export': '10/hour'
    """
    scope = 'export'
    rate = '10/hour'


# ---------------------------------------------------------------------------
# BULK PAYMENT  ← new
# ---------------------------------------------------------------------------

class BulkPaymentThrottle(UserRateThrottle):
    """
    Separate, stricter throttle for the bulk_payment action.
    Bulk operations touch Paystack for every employee in the list;
    a single runaway call could cost significant money and trigger
    Paystack's own rate limits.
    Configured in settings:
        'bulk_payment': '5/hour'
    """
    scope = 'bulk_payment'
    rate = '5/hour'