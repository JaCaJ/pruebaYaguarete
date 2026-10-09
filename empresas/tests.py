import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from empresas.models import Ciudad, Departamento


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
        self.assertContains(listado, 'id="modal-editar-departamento"')
        self.assertContains(listado, 'data-bs-target="#modal-editar-departamento"')
        self.assertNotContains(
            listado,
            f'href="{reverse("departamento-editar", args=[departamento.pk])}"',
        )
        self.assertContains(listado, 'id="modal-eliminar-departamento"')
        self.assertContains(listado, 'data-bs-target="#modal-eliminar-departamento"')

        edicion = self.client.get(
            reverse("departamento-editar", args=[departamento.pk])
        )
        self.assertRedirects(edicion, reverse("departamento-list"))

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

        cordillera = Departamento.objects.create(nombre="Cordillera")
        edicion_vacia = self.client.post(
            reverse("departamento-editar", args=[cordillera.pk]),
            {"nombre": "   "},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_vacia.status_code, 400)
        self.assertEqual(
            edicion_vacia.json()["errores"],
            ["El nombre no puede estar vacío."],
        )
        cordillera.refresh_from_db()
        self.assertEqual(cordillera.nombre, "Cordillera")

        edicion_duplicada = self.client.post(
            reverse("departamento-editar", args=[cordillera.pk]),
            {"nombre": "central"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_duplicada.status_code, 400)
        self.assertEqual(
            edicion_duplicada.json()["errores"],
            ["Ya existe un departamento con ese nombre."],
        )
        cordillera.refresh_from_db()
        self.assertEqual(cordillera.nombre, "Cordillera")

        edicion = self.client.post(
            reverse("departamento-editar", args=[cordillera.pk]),
            {"nombre": "Guairá"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion.status_code, 200)
        self.assertEqual(edicion.json()["url"], reverse("departamento-list"))
        cordillera.refresh_from_db()
        self.assertEqual(cordillera.nombre, "Guairá")

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

    def test_la_cabecera_recorre_ascendente_descendente_y_original(self):
        for nombre in ("Misiones", "Central", "Alto Paraná"):
            Departamento.objects.create(nombre=nombre)
        listado = reverse("departamento-list")

        def nombres(respuesta):
            return re.findall(r"<td>([^<]+)</td>", respuesta.content.decode())

        original = self.client.get(listado)
        self.assertEqual(nombres(original), ["Alto Paraná", "Central", "Misiones"])
        self.assertContains(original, 'aria-sort="none"')
        self.assertContains(original, 'aria-label="Ordenar por nombre ascendente"')
        self.assertRegex(
            original.content.decode(),
            rf'class="table-sort"\s+href="{listado}\?orden=asc"',
        )

        ascendente = self.client.get(listado, {"orden": "asc"})
        self.assertEqual(nombres(ascendente), ["Alto Paraná", "Central", "Misiones"])
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-label="Ordenar por nombre descendente"')
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc"',
        )

        descendente = self.client.get(listado, {"orden": "desc"})
        self.assertEqual(nombres(descendente), ["Misiones", "Central", "Alto Paraná"])
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')
        self.assertRegex(
            descendente.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}"',
        )

        invalido = self.client.get(listado, {"orden": "otra"})
        self.assertEqual(nombres(invalido), ["Alto Paraná", "Central", "Misiones"])
        self.assertContains(invalido, 'aria-sort="none"')

    def test_la_paginacion_conserva_el_orden(self):
        Departamento.objects.bulk_create(
            [Departamento(nombre=f"Departamento {numero:02d}") for numero in range(11)]
        )
        listado = reverse("departamento-list")
        primera = self.client.get(listado, {"orden": "desc"})
        self.assertContains(primera, "Departamento 10")
        self.assertNotContains(primera, "Departamento 00")
        self.assertContains(primera, "page=2&amp;orden=desc")

        segunda = self.client.get(listado, {"page": 2, "orden": "desc"})
        self.assertContains(segunda, "Departamento 00")
        self.assertNotContains(segunda, "Departamento 10")
        self.assertContains(segunda, "page=1&amp;orden=desc")

    def test_busca_por_nombre_a_la_izquierda_del_alta(self):
        for nombre in ("Misiones", "Central", "Alto Paraná"):
            Departamento.objects.create(nombre=nombre)
        listado = reverse("departamento-list")

        respuesta = self.client.get(listado, {"buscar": "  paran  "})
        html = respuesta.content.decode()
        self.assertLess(html.find('name="buscar"'), html.find("Nuevo departamento"))
        self.assertContains(respuesta, 'aria-label="Buscar departamento"')
        self.assertContains(respuesta, 'placeholder="Buscar…"')
        self.assertContains(respuesta, 'value="paran"')
        self.assertContains(respuesta, "Alto Paraná")
        self.assertNotContains(respuesta, "Misiones")
        self.assertNotContains(respuesta, ">Central<")

        sin_coincidencias = self.client.get(listado, {"buscar": "zzz"})
        self.assertContains(sin_coincidencias, "Sin resultados")
        self.assertContains(sin_coincidencias, "«zzz»")
        self.assertNotContains(sin_coincidencias, "Todavía no hay departamentos")

        ordenado = self.client.get(listado, {"buscar": "a", "orden": "desc"})
        self.assertRegex(
            ordenado.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}\?buscar=a"',
        )
        self.assertContains(ordenado, "Alto Paraná")
        self.assertContains(ordenado, "Central")
        self.assertNotContains(ordenado, "Misiones")

    def test_la_busqueda_se_conserva_al_paginar(self):
        Departamento.objects.bulk_create(
            [Departamento(nombre=f"Departamento {numero:02d}") for numero in range(11)]
        )
        listado = reverse("departamento-list")
        primera = self.client.get(listado, {"buscar": "Departamento", "orden": "desc"})
        self.assertContains(primera, "Departamento 10")
        self.assertNotContains(primera, "Departamento 00")
        self.assertContains(primera, "page=2&amp;orden=desc&amp;buscar=Departamento")

        segunda = self.client.get(
            listado,
            {"page": 2, "orden": "desc", "buscar": "Departamento"},
        )
        self.assertContains(segunda, "Departamento 00")
        self.assertNotContains(segunda, "Departamento 10")
        self.assertContains(segunda, "page=1&amp;orden=desc&amp;buscar=Departamento")


class PruebasCrudCiudad(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ana",
            password="clave-segura-1",
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.central = Departamento.objects.create(nombre="Central")
        self.itapua = Departamento.objects.create(nombre="Itapúa")

    def test_las_pantallas_exigen_sesion(self):
        self.client.logout()
        for nombre in (
            "ciudad-list",
            "ciudad-crear",
        ):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("ciudad-list"))
        self.assertContains(listado, 'id="modal-nueva-ciudad"')
        self.assertContains(listado, 'data-bs-target="#modal-nueva-ciudad"')
        self.assertContains(listado, "tom-select.popular.min.js")
        self.assertContains(listado, "tom-select.bootstrap5.min.css")
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("ciudad-crear"))
        self.assertRedirects(alta, f"{reverse('ciudad-list')}?nuevo=1")

    def test_el_menu_incluye_ciudades(self):
        respuesta = self.client.get(reverse("empresa-list"))
        self.assertContains(respuesta, 'id="menu-principal"')
        self.assertContains(respuesta, "Ciudades")
        self.assertContains(respuesta, reverse("ciudad-list"))

    def test_crear_listar_editar_y_eliminar(self):
        crear = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "  Lambaré  ", "departamento": self.central.pk},
            follow=True,
        )
        self.assertContains(crear, "Ciudad creada.")
        ciudad = Ciudad.objects.get()
        self.assertEqual(ciudad.nombre, "Lambaré")
        self.assertEqual(ciudad.departamento, self.central)

        listado = self.client.get(reverse("ciudad-list"))
        self.assertContains(listado, "Lambaré")
        self.assertContains(listado, "Central")
        self.assertContains(listado, "<th>Departamento</th>")
        self.assertContains(listado, 'id="modal-editar-ciudad"')
        self.assertContains(listado, 'data-bs-target="#modal-editar-ciudad"')
        self.assertContains(listado, f'data-departamento="{self.central.pk}"')
        self.assertNotContains(
            listado,
            f'href="{reverse("ciudad-editar", args=[ciudad.pk])}"',
        )
        self.assertContains(listado, 'id="modal-eliminar-ciudad"')
        self.assertContains(listado, 'data-bs-target="#modal-eliminar-ciudad"')

        edicion = self.client.get(reverse("ciudad-editar", args=[ciudad.pk]))
        self.assertRedirects(edicion, reverse("ciudad-list"))

        confirmacion = self.client.get(reverse("ciudad-eliminar", args=[ciudad.pk]))
        self.assertRedirects(confirmacion, reverse("ciudad-list"))

        editar = self.client.post(
            reverse("ciudad-editar", args=[ciudad.pk]),
            {"nombre": "Encarnación", "departamento": self.itapua.pk},
            follow=True,
        )
        self.assertContains(editar, "Ciudad actualizada.")
        ciudad.refresh_from_db()
        self.assertEqual(ciudad.nombre, "Encarnación")
        self.assertEqual(ciudad.departamento, self.itapua)

        self.client.post(
            reverse("ciudad-eliminar", args=[ciudad.pk]),
            follow=True,
        )
        self.assertFalse(Ciudad.objects.exists())

    def test_rechaza_nombre_vacio_duplicado_o_sin_departamento(self):
        vacio = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "   ", "departamento": self.central.pk},
        )
        self.assertContains(vacio, "El nombre no puede estar vacío.")
        self.assertContains(vacio, 'data-bs-delay="10000"')
        self.assertContains(vacio, 'data-abrir="1"')
        self.assertContains(vacio, "is-invalid")
        self.assertFalse(Ciudad.objects.exists())

        sin_departamento = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "Lambaré"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_departamento.status_code, 400)
        self.assertEqual(
            sin_departamento.json()["errores"],
            ["Seleccioná un departamento."],
        )
        self.assertEqual(sin_departamento.json()["campos"], ["departamento"])
        self.assertFalse(Ciudad.objects.exists())

        Ciudad.objects.create(nombre="Lambaré", departamento=self.central)
        duplicado = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "Lambaré", "departamento": self.central.pk},
        )
        self.assertContains(
            duplicado,
            "Ya existe una ciudad con ese nombre en ese departamento.",
        )
        self.assertEqual(Ciudad.objects.count(), 1)

        respuesta = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "Lambaré", "departamento": self.central.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["Ya existe una ciudad con ese nombre en ese departamento."],
        )

        otra_mayuscula = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "lambaré", "departamento": self.central.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otra_mayuscula.status_code, 400)
        self.assertEqual(
            otra_mayuscula.json()["errores"],
            ["Ya existe una ciudad con ese nombre en ese departamento."],
        )
        self.assertEqual(Ciudad.objects.count(), 1)

        otro_departamento = self.client.post(
            reverse("ciudad-crear"),
            {"nombre": "Lambaré", "departamento": self.itapua.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otro_departamento.status_code, 200)
        self.assertEqual(Ciudad.objects.filter(nombre="Lambaré").count(), 2)

        encarnacion = Ciudad.objects.create(nombre="Encarnación", departamento=self.itapua)
        edicion_vacia = self.client.post(
            reverse("ciudad-editar", args=[encarnacion.pk]),
            {"nombre": "   ", "departamento": self.itapua.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_vacia.status_code, 400)
        self.assertEqual(
            edicion_vacia.json()["errores"],
            ["El nombre no puede estar vacío."],
        )
        encarnacion.refresh_from_db()
        self.assertEqual(encarnacion.nombre, "Encarnación")

        edicion_duplicada = self.client.post(
            reverse("ciudad-editar", args=[encarnacion.pk]),
            {"nombre": "lambaré", "departamento": self.itapua.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_duplicada.status_code, 400)
        self.assertEqual(
            edicion_duplicada.json()["errores"],
            ["Ya existe una ciudad con ese nombre en ese departamento."],
        )
        encarnacion.refresh_from_db()
        self.assertEqual(encarnacion.nombre, "Encarnación")

        edicion = self.client.post(
            reverse("ciudad-editar", args=[encarnacion.pk]),
            {"nombre": "Filadelfia", "departamento": self.central.pk},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion.status_code, 200)
        self.assertEqual(edicion.json()["url"], reverse("ciudad-list"))
        encarnacion.refresh_from_db()
        self.assertEqual(encarnacion.nombre, "Filadelfia")
        self.assertEqual(encarnacion.departamento, self.central)

    def test_el_modelo_rechaza_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            Ciudad.objects.create(nombre="   ", departamento=self.central)

    def test_no_se_elimina_un_departamento_con_ciudades(self):
        Ciudad.objects.create(nombre="Lambaré", departamento=self.central)
        respuesta = self.client.post(
            reverse("departamento-eliminar", args=[self.central.pk]),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["No se puede eliminar el departamento porque tiene ciudades asociadas."],
        )
        self.assertTrue(Departamento.objects.filter(pk=self.central.pk).exists())

    def test_pagina_el_listado(self):
        Ciudad.objects.bulk_create(
            [
                Ciudad(nombre=f"Ciudad {numero:02d}", departamento=self.central)
                for numero in range(11)
            ]
        )
        primera = self.client.get(reverse("ciudad-list"))
        self.assertContains(primera, "Ciudad 00")
        self.assertNotContains(primera, "Ciudad 10")
        segunda = self.client.get(reverse("ciudad-list"), {"page": 2})
        self.assertContains(segunda, "Ciudad 10")
        self.assertNotContains(segunda, "Ciudad 00")

    def test_la_cabecera_recorre_ascendente_descendente_y_original(self):
        for nombre, departamento in (
            ("Lambaré", self.central),
            ("Encarnación", self.itapua),
            ("Filadelfia", self.central),
        ):
            Ciudad.objects.create(nombre=nombre, departamento=departamento)
        listado = reverse("ciudad-list")

        def nombres(respuesta):
            return re.findall(r"<tr>\s*<td>([^<]+)</td>", respuesta.content.decode())

        original = self.client.get(listado)
        self.assertEqual(nombres(original), ["Encarnación", "Filadelfia", "Lambaré"])
        self.assertContains(original, 'aria-sort="none"')
        self.assertContains(original, 'aria-label="Ordenar por nombre ascendente"')
        self.assertRegex(
            original.content.decode(),
            rf'class="table-sort"\s+href="{listado}\?orden=asc"',
        )

        ascendente = self.client.get(listado, {"orden": "asc"})
        self.assertEqual(nombres(ascendente), ["Encarnación", "Filadelfia", "Lambaré"])
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-label="Ordenar por nombre descendente"')
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc"',
        )

        descendente = self.client.get(listado, {"orden": "desc"})
        self.assertEqual(nombres(descendente), ["Lambaré", "Filadelfia", "Encarnación"])
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')
        self.assertRegex(
            descendente.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}"',
        )

        invalido = self.client.get(listado, {"orden": "otra"})
        self.assertEqual(nombres(invalido), ["Encarnación", "Filadelfia", "Lambaré"])
        self.assertContains(invalido, 'aria-sort="none"')

    def test_la_paginacion_conserva_el_orden(self):
        Ciudad.objects.bulk_create(
            [
                Ciudad(nombre=f"Ciudad {numero:02d}", departamento=self.central)
                for numero in range(11)
            ]
        )
        listado = reverse("ciudad-list")
        primera = self.client.get(listado, {"orden": "desc"})
        self.assertContains(primera, "Ciudad 10")
        self.assertNotContains(primera, "Ciudad 00")
        self.assertContains(primera, "page=2&amp;orden=desc")

        segunda = self.client.get(listado, {"page": 2, "orden": "desc"})
        self.assertContains(segunda, "Ciudad 00")
        self.assertNotContains(segunda, "Ciudad 10")
        self.assertContains(segunda, "page=1&amp;orden=desc")

    def test_busca_por_nombre_a_la_izquierda_del_alta(self):
        for nombre, departamento in (
            ("Lambaré", self.central),
            ("Encarnación", self.itapua),
            ("Filadelfia", self.central),
        ):
            Ciudad.objects.create(nombre=nombre, departamento=departamento)
        listado = reverse("ciudad-list")

        respuesta = self.client.get(listado, {"buscar": "  fila  "})
        html = respuesta.content.decode()
        self.assertLess(html.find('name="buscar"'), html.find("Nueva ciudad"))
        self.assertContains(respuesta, 'aria-label="Buscar ciudad"')
        self.assertContains(respuesta, 'placeholder="Buscar…"')
        self.assertContains(respuesta, 'value="fila"')
        self.assertContains(respuesta, "Filadelfia")
        self.assertNotContains(respuesta, "Encarnación")
        self.assertNotContains(respuesta, ">Lambaré<")

        por_departamento = self.client.get(listado, {"buscar": "itap"})
        self.assertContains(por_departamento, "Encarnación")
        self.assertNotContains(por_departamento, "Filadelfia")
        self.assertNotContains(por_departamento, ">Lambaré<")

        sin_coincidencias = self.client.get(listado, {"buscar": "zzz"})
        self.assertContains(sin_coincidencias, "Sin resultados")
        self.assertContains(sin_coincidencias, "«zzz»")
        self.assertNotContains(sin_coincidencias, "Todavía no hay ciudades")

        ordenado = self.client.get(listado, {"buscar": "a", "orden": "desc"})
        self.assertRegex(
            ordenado.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}\?buscar=a"',
        )
        self.assertContains(ordenado, "Lambaré")
        self.assertContains(ordenado, "Filadelfia")
        self.assertContains(ordenado, "Encarnación")

    def test_la_busqueda_se_conserva_al_paginar(self):
        Ciudad.objects.bulk_create(
            [
                Ciudad(nombre=f"Ciudad {numero:02d}", departamento=self.central)
                for numero in range(11)
            ]
        )
        listado = reverse("ciudad-list")
        primera = self.client.get(listado, {"buscar": "Ciudad", "orden": "desc"})
        self.assertContains(primera, "Ciudad 10")
        self.assertNotContains(primera, "Ciudad 00")
        self.assertContains(primera, "page=2&amp;orden=desc&amp;buscar=Ciudad")

        segunda = self.client.get(
            listado,
            {"page": 2, "orden": "desc", "buscar": "Ciudad"},
        )
        self.assertContains(segunda, "Ciudad 00")
        self.assertNotContains(segunda, "Ciudad 10")
        self.assertContains(segunda, "page=1&amp;orden=desc&amp;buscar=Ciudad")

    def test_sin_departamentos_pide_crear_uno(self):
        Departamento.objects.all().delete()
        listado = self.client.get(reverse("ciudad-list"))
        self.assertContains(listado, "Todavía no hay ciudades")
        self.assertContains(listado, "Primero creá un departamento")
        self.assertContains(listado, reverse("departamento-list"))
