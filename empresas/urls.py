from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from .forms import FormularioIngreso
from .views import empresa_list

urlpatterns = [
    path("", empresa_list, name="empresa-list"),
    path(
        "login/",
        login_not_required(
            auth_views.LoginView.as_view(
                template_name="registration/login.html",
                authentication_form=FormularioIngreso,
            )
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
