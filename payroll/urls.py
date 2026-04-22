from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .views import (
    UserViewSet, EmployeeViewSet, AttendanceViewSet, DeductionViewSet,
    PaymentViewSet, CompanyViewSet, SackedEmployeeViewSet, 
    NotificationViewSet, frontend,
    paystack_banks, paystack_verify_account  # Import at top
)
from .auth_views import (
    login_view, register_view, logout_view, CookieTokenRefreshView, 
    verify_password, get_next_employee_id, CurrentUserView
)
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'deductions', DeductionViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'sacked-employees', SackedEmployeeViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    # Frontend routes
    path('', frontend, name='home'),
    path('login/', frontend, name='login'),
    path('dashboard/', frontend, name='dashboard'),
    path('employees/', frontend, name='employees'),
    path('attendance/', frontend, name='attendance'),
    path('deductions/', frontend, name='deductions'),
    path('payments/', frontend, name='payments'),
    path('companies/', frontend, name='companies'),
    path('sacked-employees/', frontend, name='sacked-employees'),
    path('notifications/', frontend, name='notifications'),

    # API endpoints (router)
    path('api/', include(router.urls)),
    
    # Auth endpoints
    path('api/login/', login_view, name='api-login'),
    path('api/register/', register_view, name='api-register'),
    path('api/logout/', logout_view, name='api-logout'),
    
    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/current-user/', CurrentUserView.as_view(), name='current-user'),
    path('api/verify-password/', verify_password, name='verify_password'),
    
    # Employee ID preview
    path('api/next-employee-id/', get_next_employee_id, name='next-employee-id'),
    
    # Paystack endpoints - ONLY THESE TWO (removed duplicates)
    path('api/paystack/banks/', paystack_banks, name='paystack-banks'),
    path('api/paystack/verify-account/', paystack_verify_account, name='paystack-verify'),
]

# Static/Media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
