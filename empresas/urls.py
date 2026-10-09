from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from .forms import FormularioIngreso
from .views import (
    CrearCategoria,
    CrearCiudad,
    CrearDepartamento,
    EditarCategoria,
    EditarCiudad,
    EditarDepartamento,
    EliminarCategoria,
    EliminarCiudad,
    EliminarDepartamento,
    ListaCategorias,
    ListaCiudades,
    ListaDepartamentos,
    empresa_list,
)

urlpatterns = [
    path("", empresa_list, name="empresa-list"),
    path("departamentos/", ListaDepartamentos.as_view(), name="departamento-list"),
    path(
        "departamentos/nuevo/",
        CrearDepartamento.as_view(),
        name="departamento-crear",
    ),
    path(
        "departamentos/<int:pk>/editar/",
        EditarDepartamento.as_view(),
        name="departamento-editar",
    ),
    path(
        "departamentos/<int:pk>/eliminar/",
        EliminarDepartamento.as_view(),
        name="departamento-eliminar",
    ),
    path("ciudades/", ListaCiudades.as_view(), name="ciudad-list"),
    path("ciudades/nuevo/", CrearCiudad.as_view(), name="ciudad-crear"),
    path(
        "ciudades/<int:pk>/editar/",
        EditarCiudad.as_view(),
        name="ciudad-editar",
    ),
    path(
        "ciudades/<int:pk>/eliminar/",
        EliminarCiudad.as_view(),
        name="ciudad-eliminar",
    ),
    path("categorias/", ListaCategorias.as_view(), name="categoria-list"),
    path("categorias/nuevo/", CrearCategoria.as_view(), name="categoria-crear"),
    path(
        "categorias/<int:pk>/editar/",
        EditarCategoria.as_view(),
        name="categoria-editar",
    ),
    path(
        "categorias/<int:pk>/eliminar/",
        EliminarCategoria.as_view(),
        name="categoria-eliminar",
    ),
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
