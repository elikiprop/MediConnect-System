from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("name", "doctor", "department", "date", "time", "phone", "email", "google_meet_link")
    search_fields = ("name", "doctor", "email", "phone")
    list_filter = ("department", "date")
