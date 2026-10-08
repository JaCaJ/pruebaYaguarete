from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from empresas.models import Departamento


class PruebasCrudDepartamento(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ana",
            password="clave-segura-1",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_las_pantallas_exigen_sesion(self):
        self.client.logout()
        for nombre in (
            "departamento-list",
            "departamento-crear",
        ):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("departamento-list"))
        self.assertContains(listado, 'id="modal-nuevo-departamento"')
        self.assertContains(listado, 'data-bs-target="#modal-nuevo-departamento"')
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("departamento-crear"))
        self.assertRedirects(alta, f"{reverse('departamento-list')}?nuevo=1")

    def test_el_menu_incluye_departamentos(self):
        respuesta = self.client.get(reverse("empresa-list"))
        self.assertContains(respuesta, 'id="menu-principal"')
        self.assertContains(respuesta, "Departamentos")
        self.assertContains(respuesta, reverse("departamento-list"))

    def test_crear_listar_editar_y_eliminar(self):
        crear = self.client.post(
            reverse("departamento-crear"),
            {"nombre": "  Central  "},
            follow=True,
        )
        self.assertContains(crear, "Departamento creado.")
        departamento = Departamento.objects.get()
        self.assertEqual(departamento.nombre, "Central")

        listado = self.client.get(reverse("departamento-list"))
        self.assertContains(listado, "Central")
        self.assertContains(listado, 'id="modal-eliminar-departamento"')
        self.assertContains(listado, 'data-bs-target="#modal-eliminar-departamento"')

        confirmacion = self.client.get(
            reverse("departamento-eliminar", args=[departamento.pk])
        )
        self.assertRedirects(confirmacion, reverse("departamento-list"))

        editar = self.client.post(
            reverse("departamento-editar", args=[departamento.pk]),
            {"nombre": "Cordillera"},
            follow=True,
        )
        self.assertContains(editar, "Departamento actualizado.")
        departamento.refresh_from_db()
        self.assertEqual(departamento.nombre, "Cordillera")

        self.client.post(
            reverse("departamento-eliminar", args=[departamento.pk]),
            follow=True,
        )
        self.assertFalse(Departamento.objects.exists())

    def test_rechaza_nombre_vacio_o_duplicado(self):
        vacio = self.client.post(reverse("departamento-crear"), {"nombre": "   "})
        self.assertContains(vacio, "El nombre no puede estar vacío.")
        self.assertContains(vacio, 'data-bs-delay="10000"')
        self.assertContains(vacio, 'data-abrir="1"')
        self.assertContains(vacio, "is-invalid")
        self.assertFalse(Departamento.objects.exists())

        Departamento.objects.create(nombre="Central")
        duplicado = self.client.post(
            reverse("departamento-crear"),
            {"nombre": "Central"},
        )
        self.assertContains(duplicado, "Ya existe un departamento con ese nombre.")
        self.assertEqual(Departamento.objects.count(), 1)

        respuesta = self.client.post(
            reverse("departamento-crear"),
            {"nombre": "Central"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["Ya existe un departamento con ese nombre."],
        )

        otra_mayuscula = self.client.post(
            reverse("departamento-crear"),
            {"nombre": "central"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otra_mayuscula.status_code, 400)
        self.assertEqual(
            otra_mayuscula.json()["errores"],
            ["Ya existe un departamento con ese nombre."],
        )
        self.assertEqual(Departamento.objects.count(), 1)

    def test_el_modelo_rechaza_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            Departamento.objects.create(nombre="   ")

    def test_pagina_el_listado(self):
        Departamento.objects.bulk_create(
            [Departamento(nombre=f"Departamento {numero:02d}") for numero in range(11)]
        )
        primera = self.client.get(reverse("departamento-list"))
        self.assertContains(primera, "Departamento 00")
        self.assertNotContains(primera, "Departamento 10")
        segunda = self.client.get(reverse("departamento-list"), {"page": 2})
        self.assertContains(segunda, "Departamento 10")
        self.assertNotContains(segunda, "Departamento 00")
