# payroll/admin.py - MINIMAL VERSION
from django.contrib import admin
from .models import (
    User, Employee, Attendance, Deduction, 
    Payment, Company, SackedEmployee, Notification, OTP, ExportToken
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name', 'type', 'status']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status']

@admin.register(Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = ['id']  # Minimal - fix after migration

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'net_amount', 'status']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'location']

@admin.register(SackedEmployee)
class SackedEmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date_sacked']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'is_read']

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'code', 'is_used']

@admin.register(ExportToken)
class ExportTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'data_type', 'is_used']