from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("appointment/", views.appointment, name="appointment"),
    path("blog/", views.blog, name="blog"),
    path("contact/", views.contact, name="contact"),
    path("detail/", views.detail, name="detail"),
    path("price/", views.price, name="price"),
    path("search/", views.search, name="search"),
    path("service/", views.service, name="service"),
    path("team/", views.team, name="team"),
    path("testimonial/", views.testimonial, name="testimonial"),
    
    # Booking and Viewing Appointments
    path("book-appointment/", views.book_appointment, name="book_appointment"),
    path("view-appointments/", views.view_appointments, name="view_appointments"),

    # Notify Doctor when a patient joins a Video/Voice Call
    path("notify-doctor-video-call/<int:appointment_id>/", views.notify_doctor_video_call, name="notify_doctor_video_call"),
    path("notify-doctor-voice-call/<int:appointment_id>/", views.notify_doctor_voice_call, name="notify_doctor_voice_call"),
]
