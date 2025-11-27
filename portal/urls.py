from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from automation import views as automation_views


urlpatterns = [
    path("admin/", admin.site.urls),
    # Health check
    path("health/", automation_views.health, name="health"),
    # Landing / Home
    path("", automation_views.landing, name="home"),
    # Auth routes
    path("signup/", automation_views.signup, name="signup"),
    path("login/", automation_views.login_view, name="login"),
    path("logout/", automation_views.logout_view, name="logout"),
    # Dashboard
    path("dashboard/", automation_views.dashboard, name="dashboard"),
    # App routes (mail, templates, etc.)
    path("", include("automation.urls")),
]


