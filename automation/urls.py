from django.urls import path, include
from . import views


app_name = "automation"

urlpatterns = [
    # Keep module-specific routes here; auth and landing handled at root
    path("healthz/", views.health_check, name="healthcheck"),
    # Dashboard is handled at root level in portal/urls.py
    path("mail/", views.mail_automation, name="mail_automation"),
    path("mail/signin/start/", views.mail_signin_start, name="mail_signin_start"),
    path("mail/signin/poll/", views.mail_signin_poll, name="mail_signin_poll"),
    path("templates/", views.template_manager, name="template_manager"),
    path("templates/download/", views.template_download, name="download_templates"),
    path("templates/delete/<str:name>/", views.delete_template, name="delete_template"),
    path("templates/excel-template/", views.download_excel_template, name="download_excel_template"),
    path("report/download/", views.report_download, name="download_report"),
    path("report/download/direct/", views.download_report_direct, name="download_report_direct"),
]


