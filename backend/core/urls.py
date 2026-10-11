from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "accounts/signed-out/",
        TemplateView.as_view(template_name="dashboard/logged_out.html"),
        name="logged_out",
    ),

    # Auth (login, logout, password reset, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # Dashboard (our app) — mounted at the site root
    path("", include("dashboard.urls")),
]