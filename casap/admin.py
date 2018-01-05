from django.contrib import admin

from casap.models import *


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    model = Profile


@admin.register(EmailConfirmationCode)
class EmailConfirmationCodeAdmin(admin.ModelAdmin):
    model = EmailConfirmationCode


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    model = Volunteer


@admin.register(Vulnerable)
class VulnerableAdmin(admin.ModelAdmin):
    model = Vulnerable


@admin.register(VulnerableAddress)
class VulnerableAddressAdmin(admin.ModelAdmin):
    model = VulnerableAddress
    list_display = ("vulnerable", "address", "address_lat", "address_lng")


@admin.register(LostPersonRecord)
class LostPersonRecordAdmin(admin.ModelAdmin):
    model = LostPersonRecord
    list_display = ("vulnerable", "state", "reporter", "time", "address")


@admin.register(SightingRecord)
class SightingRecordAdmin(admin.ModelAdmin):
    model = SightingRecord
    list_display = ("reporter", "lost_record", "time", "address")


@admin.register(FindRecord)
class FindRecordAdmin(admin.ModelAdmin):
    model = FindRecord
    list_display = ("reporter", "lost_record", "time", "address")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    model = PasswordResetCode
    list_display = ("__str__", "code",)
