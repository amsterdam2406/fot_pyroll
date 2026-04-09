from django.core.validators import RegexValidator
from django.db import models
import re
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from  django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import BasePermission
# from encrypted_model_fields.fields import EncryptedCharField


class User(AbstractUser):
    """Custom User Model"""
    ROLE_ADMIN ='admin'
    ROLE_STAFF = 'staff'
    ROLE_GUARD = 'guard'
    
    ROLE_CHOICES = [
        (ROLE_ADMIN,'admin'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_GUARD, 'Guard'),
    ]
    
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='staff'
    )
    phone = models.CharField(max_length=15, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
        # Flag for admins allowed to manage companies
    is_company_admin = models.BooleanField(default=False)
    is_notification_admin = models.BooleanField(default=False)
    is_employee_admin = models.BooleanField(default=False)
    is_payment_admin = models.BooleanField(default=False)
    is_deduction_admin = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'users'

class Employee(models.Model):
    """Employee Model"""
    TYPE_CHOICES = [
        ('staff', 'Staff'),
        ('guard', 'Guard'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('terminated', 'Terminated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    location = models.CharField(max_length=200)
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Bank Details (Nigerian Banks - Naira)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=10)
    account_holder = models.CharField(max_length=200)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    join_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            with transaction.atomic():
                # Auto-generate employee ID
                last_employee = (
                    Employee.objects.select_for_update()
                    .filter(type=self.type)
                    .order_by('-created_at')
                    .first()
                )
                if last_employee and last_employee.employee_id:
                    numbers = re.findall(r'\d+', last_employee.employee_id)
                    last_number = int(numbers[0]) if numbers else 0
                    next_number = last_number + 1
                else:
                    next_number = 1
            if self.type == 'staff':
                prefix = 'FSS'
                suffix = 'Staff'
            elif self.type == 'guard':
                prefix = 'FSS'
                suffix = 'Guard'
            else:
                prefix = 'EMP'
                suffix = 'Employee'
            self.employee_id = f"{prefix}{str(next_number).zfill(4)} {suffix}"
        super().save(*args, **kwargs)

class Attendance(models.Model):
    """Attendance Model with Selfie Capture and Timestamp Tracking"""
    class Meta:
        db_table = 'attendance'
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date'],
                name='unique_employee_daily_attendance'
            )
        ]
    

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    
    # Store both time and full timestamp for accurate tracking
    clock_in = models.TimeField(blank=True, null=True)
    clock_in_timestamp = models.DateTimeField(blank=True, null=True)
    clock_in_photo = models.ImageField(upload_to='attendance/clock_in/%Y/%m/', blank=True, null=True)
    
    clock_out = models.TimeField(blank=True, null=True)
    clock_out_timestamp = models.DateTimeField(blank=True, null=True)
    clock_out_photo = models.ImageField(upload_to='attendance/clock_out/%Y/%m/', blank=True, null=True)
# later max_lenght
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    # Track if attendance qualifies for deduction (commented out for future use)
    # is_eligible_for_deduction = models.BooleanField(default=False)
    # deduction_applied = models.BooleanField(default=False)
    # deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.employee.employee_id} - {self.date}"

class Deduction(models.Model):
    """Deduction Model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('applied', 'Applied'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='deductions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.TextField()
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'deductions'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.employee.employee_id} - ₦{self.amount}"

class Payment(models.Model):
    """Payment Model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    METHOD_CHOICES = [
        ('card', 'Card Payment'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payments')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    transaction_reference = models.CharField(max_length=100, unique=True)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField()
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='processed_payments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.employee.employee_id} - ₦{self.net_amount}"

class Company(models.Model):
    """Company/Client Model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    guards_count = models.IntegerField(validators=[MinValueValidator(1)])
    payment_to_us = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_per_guard = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_payment_to_guards = models.DecimalField(max_digits=10, decimal_places=2)
    profit = models.DecimalField(max_digits=10, decimal_places=2)
    
    assigned_guards = models.ManyToManyField(Employee, related_name='assigned_companies', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.total_payment_to_guards = self.guards_count * self.payment_per_guard
        self.profit = self.payment_to_us - self.total_payment_to_guards
        super().save(*args, **kwargs)


class SackedEmployee(models.Model):
    """Archive for Terminated Employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='termination_records')
    date_sacked = models.DateField()
    offense = models.TextField()
    terminated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sacked_employees'
        ordering = ['-date_sacked']
    
    def __str__(self):
        return f"{self.employee.employee_id} - Terminated on {self.date_sacked}"

class Notification(models.Model):
    """Notification Model"""
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type}: {self.message[:50]}"

class OTP(models.Model):
    """OTP Model for payment verification"""
    email = models.EmailField()
    code = models.CharField(max_length=6,
                            validators=[RegexValidator(r'^\d{6}$', 'OTP must be a 6-digit s number.')]
                            )
    reference = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    
    class Meta:
        db_table = 'otps'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.email} - {self.reference}"
    
    def has_expired(self):
        return timezone.now() > self.expires_at

class ExportToken(models.Model):
    """Export Token Model for secure data exports"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    data_type = models.CharField(max_length=50)  # 'employees', 'payments', etc.
    filters = models.JSONField(default=dict)  # Store filter parameters
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'export_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Export token for {self.user.username} - {self.data_type}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at

# Create your models here.
