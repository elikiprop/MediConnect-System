from celery import shared_task
from datetime import timedelta
from django.utils.timezone import now
from .models import Appointment
from .utils import send_email

@shared_task
def send_appointment_reminders():
    upcoming_appointments = Appointment.objects.filter(
        date=now().date(),
        time__lte=(now() + timedelta(hours=1)).time()
    )
    
    for appointment in upcoming_appointments:
        subject = "Upcoming Appointment Reminder"
        message = f"Dear {appointment.name},\n\nThis is a reminder for your upcoming appointment with {appointment.doctor} in the {appointment.department} department.\n\n📅 Date: {appointment.date}\n⏰ Time: {appointment.time}\n\nPlease be on time.\n\nBest Regards,\nMediConnect Team"
        
        send_email(appointment.email, subject, message)
