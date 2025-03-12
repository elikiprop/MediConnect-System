from django.shortcuts import render, redirect
from .models import Appointment

# Home Page View
def home(request):
    return render(request, 'index.html')

# Static Page Views
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

# Book Appointment View
def book_appointment(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        department = request.POST.get("department")
        doctor = request.POST.get("doctor")
        date = request.POST.get("date")
        time = request.POST.get("time")

        # Save Appointment
        appointment = Appointment(
            name=name,
            email=email,
            phone=phone,
            department=department,
            doctor=doctor,
            date=date,
            time=time
        )
        appointment.save()
        
        # Redirect to View Appointments
        return redirect("{% url 'view_appointment' %}")  # Ensure this name matches urls.py

    return render(request, "appointment.html")

# View All Appointments
def view_appointments(request):
    appointments = Appointment.objects.all()  # Fetch all bookings
    return render(request, "view_appointments.html", {"appointments": appointments})
