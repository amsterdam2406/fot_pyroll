from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.conf import settings
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
from decimal import Decimal
import csv
import uuid
import base64
import secrets
import random
import string
from django.http import HttpResponse
from django.core.files.base import ContentFile
from .models import (
    Employee, Attendance, Deduction, Payment,
    Company, SackedEmployee, Notification, OTP, ExportToken
)
from .serializers import (
    UserSerializer, EmployeeSerializer, AttendanceSerializer,
    DeductionSerializer, PaymentSerializer, CompanySerializer,
    SackedEmployeeSerializer, NotificationSerializer
)
from .paystack import PaystackAPI
from .permissions import (
    IsAdmin, CanCreateEmployee, IsSackAdmin, IsPayrollAdmin,
    IsDeductionAdmin, CanEditNotification, CanViewAndEditCompany
)
from payroll.throttles import AttendanceThrottle, PaymentThrottle
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

User = get_user_model()
logger = logging.getLogger(__name__)


# USER VIEWSET

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    def get_permissions(self):
        if self.action == "export_csv":
            return [AllowAny()]
        
        if self.action == "create":
            return [IsAdmin()]
        
        if self.request.user.is_authenticated:
            if self.request.user.role in ['staff', 'guard']:
                if self.action in ['list', 'retrieve']:
                    return [IsAuthenticated()]
                return [IsAdmin()]
        return [IsAuthenticated()]
    
    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_superuser or getattr(request.user, "is_employee_admin", False)):
            return Response(
                {"error": "Only admins can delete users"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs
            )
    
    # might 
    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return User.objects.all().order_by('id')

        if user.role == 'admin':
            return User.objects.filter(role__in=['staff', 'guard']).order_by('id')
        return User.objects.filter(id=user.id).order_by('id')
    
    
    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    

# EMPLOYEE VIEWSET
    

class EmployeeViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    queryset = Employee.objects.all().order_by('id')
    serializer_class = EmployeeSerializer
    filterset_fields = ['type', 'status', 'location']
    search_fields = ['name', 'employee_id', 'email']
    # ordering_fields = ['name', 'employee_id', 'email']

    def get_permissions(self):
        user = self.request.user
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateEmployee()]
        
        if user.is_authenticated  and user.role in ['staff', 'guard']:
            if self.action in ['list', 'retrieve']:
                return [IsAuthenticated()]
            return [IsAdmin()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().destroy(request, *args, **kwargs)
        if not (request.user.is_superuser or request.user.role == 'admin' or getattr(request.user, "is_employee_admin", False)):
            return Response(
                {'error': 'Only admins can delete employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.role ==  'admin':
            return Employee.objects.all().order_by('id')
        return  Employee.objects.filter(user=user).order_by('id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, 
            methods=['post'],
            permission_classes=[IsAuthenticated, IsSackAdmin])
    def terminate(self, request, pk=None):
        employee = self.get_object()
        offense = request.data.get('offense')

        if not offense:
            return Response(
                {'error': 'Offense reason required'},
                status=400)
        with transaction.atomic():   # production safety

            SackedEmployee.objects.create(
                employee=employee,
                date_sacked=timezone.now().date(),
                offense=offense,
                terminated_by=request.user
        )

        employee.status = 'terminated'
        employee.save()

        Notification.objects.create(
            user=employee.user,  # assign to user
            message=f"Employee {employee.employee_id} - {employee.name} has been terminated. Reason: {offense}",
            type='warning'
        )

        logger.info(
            f"{request.user.username} terminated {employee.name}. Offense: {offense}"
        )

        return Response({'message': 'Employee terminated successfully'})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def request_export(self, request):
        """Request export token for employee data"""
        password = request.data.get('password')
        data_type = 'employees'
        filters = request.data.get('filters', {})
        
        # Verify password
        if not password or not request.user.check_password(password):
            return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check permissions - only admins can export full data
        user = request.user
        if not (user.is_superuser or user.role == 'admin'):
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        # Create export token
        token = secrets.token_urlsafe(32)
        export_token = ExportToken.objects.create(
            user=user,
            token=token,
            data_type=data_type,
            filters=filters,
            expires_at=timezone.now() + timezone.timedelta(minutes=10)
        )
        
        logger.info(f"Export token created for {user.username} - {data_type}")
        return Response({
            'token': token,
            'expires_at': export_token.expires_at
        })

        # --=-=--=-=---=
        
    @action(detail=False, methods=['get'], permission_classes=[AllowAny], authentication_classes=[SessionAuthentication, BasicAuthentication])
    def export_csv(self, request):
        """Export employee data as CSV using token"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            export_token = ExportToken.objects.get(token=token, is_used=False)
            if export_token.is_expired():
                return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)

            # Mark as used
            export_token.is_used = True
            export_token.save()

            # Get filtered queryset
            queryset = Employee.objects.all()
            filters = export_token.filters

            if filters.get('type'):
                queryset = queryset.filter(type=filters['type'])
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            if filters.get('location'):
                queryset = queryset.filter(location=filters['location'])

            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="employees.csv"'

            writer = csv.writer(response)
            writer.writerow([
                'Employee ID', 'Name', 'Type', 'Location', 'Salary', 
                'Email', 'Phone', 'Bank Name', 'Account Number', 'Status', 'Join Date'
            ])

            for employee in queryset:
                writer.writerow([
                    employee.employee_id,
                    employee.name,
                    employee.type,
                    employee.location,
                    employee.salary,
                    employee.email or '',
                    employee.phone or '',
                    employee.bank_name,
                    employee.account_number,
                    employee.status,
                    employee.join_date
                ])

            logger.info(f"Employee export completed for {export_token.user.username}")
            return response

        except ExportToken.DoesNotExist:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


# ATTENDANCE VIEWSET
# =============

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('id')
    serializer_class = AttendanceSerializer
    filterset_fields = ['employee', 'date', 'status']
    throttle_classes = [AttendanceThrottle]

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Attendance.objects.none()
        if user.is_superuser or user.role == 'admin':
            return Attendance.objects.all().order_by('id')
        try:
            employee = Employee.objects.get(user=user)
            return Attendance.objects.filter(employee=employee).order_by('id')
        except Employee.DoesNotExist:
            return Attendance.objects.none()

    def get_permissions(self):
        if self.action == 'process_absence_deductions':
            return [IsAdmin()]
        if self.action in ['clock_in_with_photo', 'clock_out_with_photo']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action in ['clock_in_with_photo', 'clock_out_with_photo', 'create', 'update', 'partial_update']:
            return [AttendanceThrottle()]
        return []

    def perform_create(self, serializer):
        """handles clock-in and clock-out logic safely."""
        try:
            employee = Employee.objects.get(user=self.request.user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError(
                {"error": "Employee profile not found for this user."}
            )
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=timezone.now().date()
        )

        if not attendance.clock_in_time:
            attendance.clock_in_time = timezone.now()
        elif not attendance.clock_out_time:
            attendance.clock_out_time = timezone.now()
        else:
            raise serializers.ValidationError(
                {"error": "Attendance already completed today."})
        attendance.save()


    # ------------------------------------------------------------------

    def _get_employee(self, request):
        """Return the Employee for this request, respecting admin override."""
        if request.user.is_superuser or request.user.role == 'admin':
            emp_id = request.data.get('employee_id')
            if emp_id:
                return Employee.objects.get(id=emp_id)
        return Employee.objects.get(user=request.user)

    @staticmethod
    def _decode_photo(photo_data):
        """
        Parse a base64 data URL and return (ext, raw_bytes).
        Raises ValueError on bad input.
        """
        if not photo_data:
            raise ValueError("No photo provided")
        
        # Handle data URI format: data:image/png;base64,iVBORw0KGgo...
        if ';base64,' in photo_data:
            header, imgstr = photo_data.split(';base64,', 1)
            ext = header.split('/')[-1] if '/' in header else 'jpg'
            ext = ext.replace('jpeg', 'jpg')
        elif 'base64' in photo_data:
            # Fallback for malformed data URIs
            parts = photo_data.split('base64', 1)
            if len(parts) == 2:
                imgstr = parts[1].lstrip(',;:')
                ext = 'jpg'
            else:
                raise ValueError("Invalid photo format")
        else:
            # Plain base64 without header
            imgstr = photo_data
            ext = 'jpg'

        try:
            return ext, base64.b64decode(imgstr)
        except Exception:
            raise ValueError("Invalid base64 data")

    # ---------

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def clock_in_with_photo(self, request):
        try:
            employee = self._get_employee(request)
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for photo FIRST (before checking if already clocked in)
        photo_data = request.data.get('photo')
        if not photo_data:
            return Response(
                {'error': 'Photo is required for attendance'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=timezone.now().date()
        )

        if attendance.clock_in_timestamp:
            return Response(
                {'error': 'Already clocked in today'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ext, image_data = self._decode_photo(photo_data)
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save photo and clock in
        attendance.clock_in_photo.save(
            f'clockin_{employee.id}_{timezone.now().timestamp()}.{ext}',
            ContentFile(image_data),
            save=False
        )
        attendance.clock_in_timestamp = timezone.now()
        attendance.clock_in = timezone.now().time()
        attendance.status = 'present'
        attendance.save()
        logger.info(f"{request.user.username} clocked in with photo")
        return Response({
            'message': 'Clocked in successfully',
            'status': 'present'
        })


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def clock_out_with_photo(self, request):
        try:
            employee = self._get_employee(request)
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for attendance record FIRST (before validating photo)
        try:
            attendance = Attendance.objects.get(
                employee=employee,
                date=timezone.now().date()
            )
        except Attendance.DoesNotExist:
            return Response(
                {'error': 'No clock-in record found for today'},
                status=status.HTTP_404_NOT_FOUND
            )

        if attendance.clock_out_timestamp:
            return Response(
                {'error': 'Already clocked out today'},
                status=status.HTTP_400_BAD_REQUEST  # Changed to 400 as this is a business logic error
            )

        photo_data = request.data.get('photo')
        if not photo_data:
            return Response(
                {'error': 'Photo is required for clock out'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            ext, image_data = self._decode_photo(photo_data)
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST  # Changed to 400 for invalid data
            )

        # Save photo and clock out
        attendance.clock_out_photo.save(
            f'clockout_{employee.id}_{timezone.now().timestamp()}.{ext}',
            ContentFile(image_data),
            save=False
        )
        attendance.clock_out_timestamp = timezone.now()
        attendance.clock_out = timezone.now().time()
        attendance.status = 'present'
        attendance.save()
        logger.info(f"{request.user.username} clocked out with photo")
        return Response({'message': 'Clocked out successfully'})

    # ------------------------------------------------------------------
    # ABSENCE DEDUCTIONS (admin only)
    # ------------------------------------------------------------------

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def process_absence_deductions(self, request):
        """
        Process salary deductions for employees with 3+ consecutive days of absence.
        """
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=10)

        employees = Employee.objects.filter(status='active')
        processed_deductions = []
        errors = []

        for employee in employees:
            try:
                # Find attendance dates in range
                attendance_dates = set(
                    Attendance.objects.filter(
                        employee=employee,
                        date__range=[start_date, end_date]
                    ).values_list('date', flat=True)
                )

                # Generate all weekdays in range
                all_dates = set()
                current_date = start_date
                while current_date <= end_date:
                    if current_date.weekday() < 5:  # Monday-Friday
                        all_dates.add(current_date)
                    current_date += timezone.timedelta(days=1)

                # Find missing dates (absences)
                absences = sorted(all_dates - attendance_dates)
                
                # Calculate consecutive absences
                max_consecutive = 0
                consecutive = 0
                prev_date = None

                for absence_date in absences:
                    if prev_date is None or (absence_date - prev_date).days == 1:
                        consecutive += 1
                        max_consecutive = max(max_consecutive, consecutive)
                    else:
                        consecutive = 1
                    prev_date = absence_date

                # Apply deduction for 3+ consecutive absences
                if max_consecutive >= 3:
                    deduction_amount = (employee.salary / 30) * max_consecutive

                    # CRITICAL FIX: Remove created_by if field doesn't exist
                    # Check if Deduction model has created_by field first
                    deduction_data = {
                        'employee': employee,
                        'amount': deduction_amount,
                        'reason': f'Absence deduction: {max_consecutive} consecutive days absent',
                        'status': 'pending',
                        'date': timezone.now().date(),
                    }
                    
                    # Only add created_by if the field exists in model
                    try:
                        Deduction.objects.create(**deduction_data, created_by=request.user)
                    except TypeError:
                        # Field doesn't exist, create without it
                        Deduction.objects.create(**deduction_data)

                    processed_deductions.append({
                        'employee': employee.name,
                        'consecutive_absences': max_consecutive,
                        'deduction_amount': deduction_amount
                    })

                    logger.info(f"Created absence deduction for {employee.name}: {deduction_amount}")

            except Exception as e:
                errors.append(f"Error processing {employee.name}: {str(e)}")
                logger.error(f"Error processing absence deductions for {employee.name}: {e}")

        return Response({
            'message': f'Processed deductions for {len(processed_deductions)} employees',
            'deductions': processed_deductions,
            'errors': errors
        })


# ============
# PAYMENT VIEWSEt
    
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('id')
    serializer_class = PaymentSerializer
    filterset_fields = ['employee', 'status', 'payment_date']
    throttle_classes = [PaymentThrottle]

    def get_permissions(self):
        """
        Apply IsPayrollAdmin for payment operations:
        - initiate_payment
        - create, update, partial_update. destroy
        """
        if self.action in ["initiate_payment", "create", "update",  "partial_update", "destroy"]:
            return [IsAuthenticated(), IsPayrollAdmin()]
        # vieewing paym lis/retri, restrr byyyRole
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # speci_Admin n superadmin see all
        if user.is_superuser or user.role == 'admin' or getattr(user, 'is_payment_admin', False):
            return Payment.objects.all().order_by('id')
        return Payment.objects.filter(employee__user=user).order_by('id')
    

    @action(detail=False, methods=['post'],
            permission_classes=[IsAuthenticated, IsPayrollAdmin, IsAdmin]
            )
    def initiate_payment(self, request):
        employee_id = request.data.get('employee_id')
        if not employee_id:
            return Response({'error': 'Employee ID required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():

            pending = Deduction.objects.filter(
                employee=employee,
                status='pending'
            ).aggregate(Sum('amount'))['amount__sum'] or 0

        net_salary = employee.salary - pending

        payment = Payment.objects.create(
            employee=employee,
            base_salary=employee.salary,
            total_deductions=pending,
            net_amount=net_salary,
            transaction_reference=str(uuid.uuid4()),
            payment_date=timezone.now().date(),
            processed_by=request.user,
            status='processing'
        )

        paystack = PaystackAPI()
        result = paystack.initialize_transaction(
            email=employee.email,
            amount=int(net_salary * 100),
            reference=payment.transaction_reference
        )

        if result.get('status'):
            logger.info(
                f"{request.user.username} initiated payment for {employee.name}"
            )
            if not employee.email:
                return Response({'error': 'Employee has no email'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            otp_code = OTP.objects.create(
                email=employee.email,
                code=otp_code,
                reference=payment.transaction_reference,
                expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )
            
            # Send OTP email
            try:
                send_mail(
                    'Payment Verification OTP',
                    f'Your OTP for payment verification is: {otp_code}\n\nThis OTP expires in 5 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [employee.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send OTP email: {e}")
            
            return Response({
                **result.get('data'),
                'otp_sent': True
            })

        payment.status = 'failed'
        payment.save()
        return Response(
            {'error': 'Payment failed'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsPayrollAdmin])
    def bulk_payment(self, request):
        employee_ids = request.data.get('employee_ids', [])
        if not employee_ids:
            return Response({'error': 'No employees selected'}, status=status.HTTP_400_BAD_REQUEST)
        
        payments_created = []
        errors = []
        
        for emp_id in employee_ids:
            try:
                employee = Employee.objects.get(id=emp_id, status='active')
                
                # Calculate deductions
                pending_deductions = Deduction.objects.filter(
                    employee=employee, status='pending'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                net_amount = employee.salary - pending_deductions
                
                # Create payment record
                payment = Payment.objects.create(
                    employee=employee,
                    base_salary=employee.salary,
                    total_deductions=pending_deductions,
                    net_amount=net_amount,
                    transaction_reference=str(uuid.uuid4()),
                    payment_date=timezone.now().date(),
                    processed_by=request.user,
                    status='processing'
                )
                
                # Initialize Paystack payment
                paystack = PaystackAPI()
                result = paystack.initialize_transaction(
                    email=employee.email,
                    amount=int(net_amount * 100),
                    reference=payment.transaction_reference
                )
                
                if result.get('status'):
                    payments_created.append({
                        'employee': employee.name,
                        'reference': payment.transaction_reference,
                        'authorization_url': result['data']['authorization_url']
                    })
                else:
                    payment.status = 'failed'
                    payment.save()
                    errors.append(f"Failed to initialize payment for {employee.name}")
                    
            except Employee.DoesNotExist:
                errors.append(f"Employee with ID {emp_id} not found")
            except Exception as e:
                errors.append(f"Error processing payment for employee ID {emp_id}: {str(e)}")
        
        return Response({
            'message': f'Processed {len(payments_created)} payments successfully',
            'payments': payments_created,
            'errors': errors
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_payment(self, request):
        reference = request.data.get('reference')
        otp_code = request.data.get('otp')
        
        if not reference:
            return Response({'error': 'Reference required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(transaction_reference=reference)
            
            # Verify OTP if provided
            if otp_code:
                try:
                    otp = OTP.objects.get(
                        reference=reference,
                        code=otp_code,
                        is_used=False
                    )
                    if otp.failed_attempts >= 3:
                        raise ValidationError('Too many failed OTP attempts. Request a new OTP.')
                    if otp.has_expired():
                        return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
                    if otp.code != otp_code:
                        otp.failed_attempts += 1
                        otp.save()
                        raise ValidationError('Incorrect OTP')
                    otp.is_used = True
                    otp.save()
                except OTP.DoesNotExist:
                    return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check with Paystack
            paystack = PaystackAPI()
            verification = paystack.verify_transaction(reference)
            
            if verification.get('status') and verification['data']['status'] == 'success':
                payment.status = 'completed'
                payment.paystack_reference = verification['data']['reference']
                payment.save()
                Notification.objects.create(
                    user=payment.employee.user,
                    message=(
                        f"Payment credited for {payment.employee.employee_id} - {payment.employee.name}: "
                        f"₦{payment.net_amount}"
                    ),
                    type='success'
                )
                
                # Mark deductions as applied
                Deduction.objects.filter(
                    employee=payment.employee, 
                    status='pending'
                ).update(status='applied')
                
                logger.info(f"Payment verified for {payment.employee.name}")
                return Response({'message': 'Payment verified successfully'})
            else:
                payment.status = 'failed'
                payment.save()
                return Response({'error': 'Payment verification failed'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def resend_otp(self, request):
        reference = request.data.get('reference')
        if not reference:
            return Response({'error': 'Reference required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = Payment.objects.get(transaction_reference=reference)
            
            if not payment.employee.email:
                return Response({'error': 'Employee has no email'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate new OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            otp = OTP.objects.create(
                email=payment.employee.email,
                code=otp_code,
                reference=reference,
                expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )
            
            # Send OTP email
            try:
                send_mail(
                    'Payment Verification OTP - Resent',
                    f'Your new OTP for payment verification is: {otp_code}\n\nThis OTP expires in 5 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [payment.employee.email],
                    fail_silently=False,
                )
                return Response({'message': 'OTP sent successfully'})
            except Exception as e:
                logger.error(f"Failed to send OTP email: {e}")
                return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "completed":
            return Response(
                {"error": "Completed payments cannot be modified"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)
    

#  dEDUCTION VIEWSET
# =========
class DeductionViewSet(viewsets.ModelViewSet):
    queryset = Deduction.objects.all().order_by('id')
    serializer_class = DeductionSerializer
    filterset_fields = ["employee", "status", "date"]

    def get_permissions(self):
        """
        - create/update/delete → only superuser or specified admin
        - list/retrieve → authenticated (filtered by queryset)
        """
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsDeductionAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.role == 'admin' or getattr(user, "is_deduction_admin", False):
            return Deduction.objects.all().order_by('id')

        if user.role in ["staff", "guard"]:
            return Deduction.objects.filter(employee__user=user).order_by('id')
        return Deduction.objects.none()

    def perform_create(self, serializer):
        deduction = serializer.save()
        Notification.objects.create(
            user=deduction.employee.user,
            message=(
                f"Deduction added for {deduction.employee.employee_id} - {deduction.employee.name}: "
                f"₦{deduction.amount}. Reason: {deduction.reason}"
            ),
            type='warning'
        )
    
#   SACKED EMPLOY VIEWSet (READ ONLY)
# ===
    
class SackedEmployeeViewSet(viewsets.ModelViewSet):
    queryset = SackedEmployee.objects.all().order_by('id')
    serializer_class = SackedEmployeeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSackAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
    
        if user.is_superuser or user.role == 'admin' or getattr(user, "is_employee_admin", False):
            return SackedEmployee.objects.all().order_by('id')
        if user.role in ["staff", "guard"]:
            return SackedEmployee.objects.filter(employee__user=user).order_by('id')
        return SackedEmployee.objects.none()
    
# NOTIFICATIONS

class NotificationViewSet(viewsets.ModelViewSet): 
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, CanEditNotification]
    queryset = Notification.objects.all().order_by('id')

    def get_queryset(self):
        user = self.request.user
        # admin view all (soeci) super user
        if user.is_superuser or user.role == 'admin' or getattr(user, 'is_notification_admin', False):
            return Notification.objects.all().order_by('id')
        return Notification.objects.filter(user=user).order_by('id')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        qs = self.get_queryset()
        qs.update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


# =======
# COMPANY plans huh
class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('id')
    serializer_class = CompanySerializer
    permission_classes = [CanViewAndEditCompany]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return Company.objects.all().order_by('id')
        if user.role in ['staff', 'guard']:
            return Company.objects.filter(assigned_guards__user=user).distinct().order_by('id')
        return Company.objects.none()


def frontend(request):
    return render(request, "frontend/index.html")
    