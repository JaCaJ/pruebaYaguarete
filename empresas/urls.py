from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from .forms import FormularioIngreso
from .views import (
    CrearCategoria,
    CrearCiudad,
    CrearContacto,
    CrearDepartamento,
    CrearDireccion,
    CrearEmpresa,
    EditarCategoria,
    EditarCiudad,
    EditarContacto,
    EditarDepartamento,
    EditarDireccion,
    EditarEmpresa,
    EliminarCategoria,
    EliminarCiudad,
    EliminarContacto,
    EliminarDepartamento,
    EliminarDireccion,
    EliminarEmpresa,
    ListaCategorias,
    ListaCiudades,
    ListaContactos,
    ListaDepartamentos,
    ListaDirecciones,
    ListaEmpresas,
)

urlpatterns = [
    path("", ListaEmpresas.as_view(), name="empresa-list"),
    path("empresas/nuevo/", CrearEmpresa.as_view(), name="empresa-crear"),
    path(
        "empresas/<int:pk>/editar/",
        EditarEmpresa.as_view(),
        name="empresa-editar",
    ),
    path(
        "empresas/<int:pk>/eliminar/",
        EliminarEmpresa.as_view(),
        name="empresa-eliminar",
    ),
    path("contactos/", ListaContactos.as_view(), name="contacto-list"),
    path("contactos/nuevo/", CrearContacto.as_view(), name="contacto-crear"),
    path(
        "contactos/<int:pk>/editar/",
        EditarContacto.as_view(),
        name="contacto-editar",
    ),
    path(
        "contactos/<int:pk>/eliminar/",
        EliminarContacto.as_view(),
        name="contacto-eliminar",
    ),
    path("direcciones/", ListaDirecciones.as_view(), name="direccion-list"),
    path("direcciones/nuevo/", CrearDireccion.as_view(), name="direccion-crear"),
    path(
        "direcciones/<int:pk>/editar/",
        EditarDireccion.as_view(),
        name="direccion-editar",
    ),
    path(
        "direcciones/<int:pk>/eliminar/",
        EliminarDireccion.as_view(),
        name="direccion-eliminar",
    ),
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
