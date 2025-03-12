from django.shortcuts import render, redirect
from django.conf import settings
from datetime import datetime, timedelta
from .models import Appointment
from .utils import send_sms, format_phone_number  # ✅ Import Twilio functions

# Home Page View
def home(request):
    return render(request, 'index.html')

# Static Pages
def about(request):
    return render(request, 'about.html')

def appointment(request):
    return render(request, 'appointment.html')

def blog(request):
    return render(request, 'blog.html')

def contact(request):
    return render(request, 'contact.html')

def detail(request):
    return render(request, 'detail.html')

def price(request):
    return render(request, 'price.html')

def search(request):
    return render(request, 'search.html')

def service(request):
    return render(request, 'service.html')

def team(request):
    return render(request, 'team.html')

def testimonial(request):
    return render(request, 'testimonial.html')

# ✅ Booking an appointment
def book_appointment(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        phone = format_phone_number(phone)  # ✅ Convert phone to correct format
        department = request.POST.get("department")
        doctor = request.POST.get("doctor")
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")

        try:
            # ✅ Convert string date and time to a datetime object
            appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # ✅ Save appointment to database
            appointment = Appointment(
                name=name, email=email, phone=phone,
                department=department, doctor=doctor,
                date=appointment_datetime.date(),
                time=appointment_datetime.time()
            )
            appointment.save()

            # ✅ Send booking confirmation SMS
            confirmation_message = f"Dear {name}, your appointment with {doctor} on {date_str} at {time_str} is confirmed."
            send_sms(phone, confirmation_message)

            return redirect("view_appointments")
        except ValueError:
            return render(request, "appointment.html", {"error": "Invalid date or time format."})

    return render(request, "appointment.html")

# ✅ View booked appointments
def view_appointments(request):
    appointments = Appointment.objects.all().order_by('-date', '-time')  # Fetch and sort by latest first
    return render(request, "view_appointments.html", {"appointments": appointments})
