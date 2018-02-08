from django.contrib import admin
from django.contrib.gis import admin

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


@admin.register(Activity)
class ActivityAdmin(admin.OSMGeoAdmin):
    search_fields = ['category', 'person__name', 'time', 'activity_type']
    raw_id_fields = ('location',)
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12
    readonly_fields = ('locLat', 'locLon')


@admin.register(LostActivity)
class LostActivityAdmin(admin.OSMGeoAdmin):
    search_fields = ['category', 'person__name', 'time', 'activity_type']
    raw_id_fields = ('location',)
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12
    readonly_fields = ('locLat', 'locLon')


@admin.register(FoundActivity)
class FoundActivityAdmin(admin.OSMGeoAdmin):
    search_fields = ['category', 'person__name', 'time', 'activity_type']
    raw_id_fields = ('location',)
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12
    readonly_fields = ('locLat', 'locLon')


@admin.register(Location)
class LocationAdmin(admin.OSMGeoAdmin):
    search_fields = ['name', 'description', 'addit_info']
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12


@admin.register(VolunteerAvailability)
class VolunteerAvailabilityAdmin(admin.ModelAdmin):
    model = VolunteerAvailability
    list_display = ("volunteer", "address", "address_lat", "address_lng", "time_from", "time_to", "km_radius")
