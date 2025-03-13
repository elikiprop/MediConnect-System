from django.urls import path
from . import views

urlpatterns = [
    # ✅ Authentication Routes
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),

    # ✅ Home Page & Static Pages
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

    # ✅ Dashboards
    path("patient-dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("doctor-dashboard/", views.doctor_dashboard, name="doctor_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # ✅ Appointments
    path("book-appointment/", views.book_appointment, name="book_appointment"),
    path("view-appointments/", views.view_appointments, name="view_appointments"),
    path("delete-appointment/<int:appointment_id>/", views.delete_appointment, name="delete_appointment"),
    path("reschedule-appointment/<int:appointment_id>/", views.reschedule_appointment, name="reschedule_appointment"),

    # ✅ Video & Voice Calls
    path("notify-doctor-video-call/<int:appointment_id>/", views.notify_doctor_video_call, name="notify_doctor_video_call"),
    path("notify-doctor-voice-call/<int:appointment_id>/", views.notify_doctor_voice_call, name="notify_doctor_voice_call"),

    # ✅ Medical Records
    path("add-medical-record/", views.add_edit_medical_record, name="add_medical_record"),
    path("edit-medical-record/<int:record_id>/", views.add_edit_medical_record, name="edit_medical_record"),
    path("generate-medical-record-pdf/<int:record_id>/", views.generate_pdf, name="generate_pdf"),

    # ✅ Patient Referral
    path("refer-patient/", views.refer_patient, name="refer_patient"),
]
