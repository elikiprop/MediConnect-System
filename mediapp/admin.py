from django.contrib import admin
from .models import Appointment, CustomUser, Doctor, MedicalRecord, PatientReferral

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'patient', 'doctor', 'department', 'date', 'time', 'voice_call_link', 'video_call_link']
    list_filter = ['date', 'doctor', 'department']
    search_fields = ['name', 'patient__username', 'doctor__user__username', 'department']
    date_hierarchy = 'date'
    
    
admin.site.register(CustomUser)
admin.site.register(Doctor)
admin.site.register(MedicalRecord)
admin.site.register(PatientReferral)
