from celery import shared_task
from datetime import timedelta
from django.utils.timezone import now
from .models import Appointment
from .utils import send_email

@shared_task
def send_appointment_reminders():
    current_time = now()
    upcoming_appointments = Appointment.objects.filter(
        date=current_time.date(),
        time__gte=current_time.time(),
        time__lte=(current_time + timedelta(hours=1)).time()
    )
    
    for appointment in upcoming_appointments:
        subject = "Upcoming Appointment Reminder"
        message = f"Dear {appointment.name},\n\nThis is a reminder for your upcoming appointment with Dr. {appointment.doctor.user.username} in the {appointment.department} department.\n\n📅 Date: {appointment.date}\n⏰ Time: {appointment.time}\n\nPlease be on time.\n\nBest Regards,\nMediConnect Team"
        
        # Make sure that send_email is defined properly in utils.py
        send_email(appointment.email, subject, message)