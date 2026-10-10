import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from empresas.models import Categoria, Ciudad, Contacto, Departamento, Direccion, Empresa

RUC_VALIDO = "80012345-0"


def _datos_empresa(**extra):
    datos = {
        "razon_social": "Acme S.A.",
        "ruc": RUC_VALIDO,
        "email": "",
        "telefono": "",
        "es_cliente": "on",
        "activo": "on",
    }
    datos.update(extra)
    return datos


def _crear_empresa(usuario, **kwargs):
    valores = {
        "razon_social": "Acme S.A.",
        "ruc": RUC_VALIDO,
        "es_cliente": True,
        "usuario_creacion": usuario,
        "usuario_modificacion": usuario,
    }
    valores.update(kwargs)
    return Empresa.objects.create(**valores)


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
        self.assertContains(listado, ">Departamento</a>")
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

    def test_la_cabecera_de_departamento_recorre_ascendente_descendente_y_original(self):
        for nombre, departamento in (
            ("Lambaré", self.central),
            ("Encarnación", self.itapua),
            ("Filadelfia", self.central),
        ):
            Ciudad.objects.create(nombre=nombre, departamento=departamento)
        listado = reverse("ciudad-list")

        def filas(respuesta):
            return re.findall(
                r"<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        original = self.client.get(listado)
        self.assertContains(original, 'aria-label="Ordenar por departamento ascendente"')
        self.assertRegex(
            original.content.decode(),
            rf'class="table-sort"\s+href="{listado}\?orden=asc&amp;columna=departamento"',
        )

        ascendente = self.client.get(
            listado, {"orden": "asc", "columna": "departamento"}
        )
        self.assertEqual(
            filas(ascendente),
            [
                ("Filadelfia", "Central"),
                ("Lambaré", "Central"),
                ("Encarnación", "Itapúa"),
            ],
        )
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-sort="none"')
        self.assertContains(
            ascendente, 'aria-label="Ordenar por departamento descendente"'
        )
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=departamento"',
        )

        descendente = self.client.get(
            listado, {"orden": "desc", "columna": "departamento"}
        )
        self.assertEqual(
            filas(descendente),
            [
                ("Encarnación", "Itapúa"),
                ("Filadelfia", "Central"),
                ("Lambaré", "Central"),
            ],
        )
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')
        self.assertRegex(
            descendente.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}"',
        )

        con_busqueda = self.client.get(
            listado,
            {"buscar": "a", "orden": "asc", "columna": "departamento"},
        )
        self.assertRegex(
            con_busqueda.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=departamento&amp;buscar=a"',
        )
        self.assertContains(con_busqueda, 'name="columna" value="departamento"')

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


class PruebasCrudCategoria(TestCase):
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
            "categoria-list",
            "categoria-crear",
        ):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("categoria-list"))
        self.assertContains(listado, 'id="modal-nueva-categoria"')
        self.assertContains(listado, 'data-bs-target="#modal-nueva-categoria"')
        self.assertContains(
            listado,
            "Descripción\n                <span class=\"fw-normal text-secondary ms-2\">Opcional. Hasta 255 caracteres.</span>",
        )
        self.assertContains(listado, "Todavía no hay categorías")
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("categoria-crear"))
        self.assertRedirects(alta, f"{reverse('categoria-list')}?nuevo=1")

    def test_el_menu_incluye_categorias(self):
        respuesta = self.client.get(reverse("empresa-list"))
        self.assertContains(respuesta, 'id="menu-principal"')
        self.assertContains(respuesta, "Categorías")
        self.assertContains(respuesta, reverse("categoria-list"))

    def test_crear_listar_editar_y_eliminar(self):
        crear = self.client.post(
            reverse("categoria-crear"),
            {"nombre": "  Cliente  ", "descripcion": "  Empresas cliente  "},
            follow=True,
        )
        self.assertContains(crear, "Categoría creada.")
        categoria = Categoria.objects.get()
        self.assertEqual(categoria.nombre, "Cliente")
        self.assertEqual(categoria.descripcion, "Empresas cliente")

        listado = self.client.get(reverse("categoria-list"))
        self.assertContains(listado, "Cliente")
        self.assertContains(listado, "Empresas cliente")
        self.assertContains(listado, 'id="modal-editar-categoria"')
        self.assertContains(listado, 'data-bs-target="#modal-editar-categoria"')
        self.assertContains(listado, 'data-descripcion="Empresas cliente"')
        self.assertNotContains(
            listado,
            f'href="{reverse("categoria-editar", args=[categoria.pk])}"',
        )
        self.assertContains(listado, 'id="modal-eliminar-categoria"')
        self.assertContains(listado, 'data-bs-target="#modal-eliminar-categoria"')

        edicion = self.client.get(reverse("categoria-editar", args=[categoria.pk]))
        self.assertRedirects(edicion, reverse("categoria-list"))

        confirmacion = self.client.get(
            reverse("categoria-eliminar", args=[categoria.pk])
        )
        self.assertRedirects(confirmacion, reverse("categoria-list"))

        editar = self.client.post(
            reverse("categoria-editar", args=[categoria.pk]),
            {"nombre": "Proveedor", "descripcion": "  "},
            follow=True,
        )
        self.assertContains(editar, "Categoría actualizada.")
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, "Proveedor")
        self.assertEqual(categoria.descripcion, "")

        sin_descripcion = self.client.get(reverse("categoria-list"))
        self.assertContains(sin_descripcion, "Proveedor")
        self.assertContains(sin_descripcion, "—")

        self.client.post(
            reverse("categoria-eliminar", args=[categoria.pk]),
            follow=True,
        )
        self.assertFalse(Categoria.objects.exists())

    def test_rechaza_nombre_vacio_o_duplicado(self):
        vacio = self.client.post(reverse("categoria-crear"), {"nombre": "   "})
        self.assertContains(vacio, "El nombre no puede estar vacío.")
        self.assertContains(vacio, 'data-bs-delay="10000"')
        self.assertContains(vacio, 'data-abrir="1"')
        self.assertContains(vacio, "is-invalid")
        self.assertFalse(Categoria.objects.exists())

        Categoria.objects.create(nombre="Cliente")
        duplicado = self.client.post(
            reverse("categoria-crear"),
            {"nombre": "Cliente"},
        )
        self.assertContains(duplicado, "Ya existe una categoría con ese nombre.")
        self.assertEqual(Categoria.objects.count(), 1)

        respuesta = self.client.post(
            reverse("categoria-crear"),
            {"nombre": "Cliente"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["Ya existe una categoría con ese nombre."],
        )
        self.assertEqual(respuesta.json()["campos"], ["nombre"])

        otra_mayuscula = self.client.post(
            reverse("categoria-crear"),
            {"nombre": "cliente"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otra_mayuscula.status_code, 400)
        self.assertEqual(
            otra_mayuscula.json()["errores"],
            ["Ya existe una categoría con ese nombre."],
        )
        self.assertEqual(Categoria.objects.count(), 1)

        proveedor = Categoria.objects.create(nombre="Proveedor")
        edicion_vacia = self.client.post(
            reverse("categoria-editar", args=[proveedor.pk]),
            {"nombre": "   "},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_vacia.status_code, 400)
        self.assertEqual(
            edicion_vacia.json()["errores"],
            ["El nombre no puede estar vacío."],
        )
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, "Proveedor")

        edicion_duplicada = self.client.post(
            reverse("categoria-editar", args=[proveedor.pk]),
            {"nombre": "cliente"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_duplicada.status_code, 400)
        self.assertEqual(
            edicion_duplicada.json()["errores"],
            ["Ya existe una categoría con ese nombre."],
        )
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, "Proveedor")

        edicion = self.client.post(
            reverse("categoria-editar", args=[proveedor.pk]),
            {"nombre": "Servicios", "descripcion": "Mantenimiento"},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion.status_code, 200)
        self.assertEqual(edicion.json()["url"], reverse("categoria-list"))
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, "Servicios")
        self.assertEqual(proveedor.descripcion, "Mantenimiento")

    def test_el_modelo_rechaza_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            Categoria.objects.create(nombre="   ")

    def test_rechaza_descripcion_demasiado_larga(self):
        listado = self.client.get(reverse("categoria-list"))
        self.assertContains(listado, 'maxlength="255"')

        respuesta = self.client.post(
            reverse("categoria-crear"),
            {"nombre": "Cliente", "descripcion": "a" * 256},
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["La descripción no puede superar los 255 caracteres."],
        )
        self.assertEqual(respuesta.json()["campos"], ["descripcion"])
        self.assertFalse(Categoria.objects.exists())

        with self.assertRaises(ValidationError):
            Categoria.objects.create(nombre="Cliente", descripcion="a" * 256)

    def test_pagina_el_listado(self):
        Categoria.objects.bulk_create(
            [Categoria(nombre=f"Categoría {numero:02d}") for numero in range(11)]
        )
        primera = self.client.get(reverse("categoria-list"))
        self.assertContains(primera, "Categoría 00")
        self.assertNotContains(primera, "Categoría 10")
        segunda = self.client.get(reverse("categoria-list"), {"page": 2})
        self.assertContains(segunda, "Categoría 10")
        self.assertNotContains(segunda, "Categoría 00")

    def test_la_cabecera_recorre_ascendente_descendente_y_original(self):
        for nombre in ("Servicios", "Cliente", "Alimentos"):
            Categoria.objects.create(nombre=nombre)
        listado = reverse("categoria-list")

        def nombres(respuesta):
            return re.findall(r"<td>([^<]+)</td>", respuesta.content.decode())

        original = self.client.get(listado)
        self.assertEqual(nombres(original), ["Alimentos", "Cliente", "Servicios"])
        self.assertContains(original, 'aria-sort="none"')
        self.assertContains(original, 'aria-label="Ordenar por nombre ascendente"')
        self.assertRegex(
            original.content.decode(),
            rf'class="table-sort"\s+href="{listado}\?orden=asc"',
        )

        ascendente = self.client.get(listado, {"orden": "asc"})
        self.assertEqual(nombres(ascendente), ["Alimentos", "Cliente", "Servicios"])
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-label="Ordenar por nombre descendente"')
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc"',
        )

        descendente = self.client.get(listado, {"orden": "desc"})
        self.assertEqual(nombres(descendente), ["Servicios", "Cliente", "Alimentos"])
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')
        self.assertRegex(
            descendente.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}"',
        )

        invalido = self.client.get(listado, {"orden": "otra"})
        self.assertEqual(nombres(invalido), ["Alimentos", "Cliente", "Servicios"])
        self.assertContains(invalido, 'aria-sort="none"')

    def test_la_cabecera_de_descripcion_recorre_ascendente_descendente_y_original(self):
        for nombre, descripcion in (
            ("Servicios", "Mantenimiento"),
            ("Cliente", "Empresas"),
            ("Alimentos", ""),
        ):
            Categoria.objects.create(nombre=nombre, descripcion=descripcion)
        listado = reverse("categoria-list")

        def filas(respuesta):
            return re.findall(
                r"<tr>\s*<td>([^<]+)</td>\s*<td>(.*?)</td>",
                respuesta.content.decode(),
            )

        original = self.client.get(listado)
        self.assertContains(
            original, 'aria-label="Ordenar por descripción ascendente"'
        )
        self.assertRegex(
            original.content.decode(),
            rf'class="table-sort"\s+href="{listado}\?orden=asc&amp;columna=descripcion"',
        )

        ascendente = self.client.get(
            listado, {"orden": "asc", "columna": "descripcion"}
        )
        self.assertEqual(
            [nombre for nombre, _descripcion in filas(ascendente)],
            ["Alimentos", "Cliente", "Servicios"],
        )
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-sort="none"')
        self.assertContains(
            ascendente, 'aria-label="Ordenar por descripción descendente"'
        )
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=descripcion"',
        )

        descendente = self.client.get(
            listado, {"orden": "desc", "columna": "descripcion"}
        )
        self.assertEqual(
            [nombre for nombre, _descripcion in filas(descendente)],
            ["Servicios", "Cliente", "Alimentos"],
        )
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')
        self.assertRegex(
            descendente.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}"',
        )

        con_busqueda = self.client.get(
            listado,
            {"buscar": "e", "orden": "asc", "columna": "descripcion"},
        )
        self.assertRegex(
            con_busqueda.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=descripcion&amp;buscar=e"',
        )
        self.assertContains(con_busqueda, 'name="columna" value="descripcion"')

    def test_la_paginacion_conserva_el_orden(self):
        Categoria.objects.bulk_create(
            [Categoria(nombre=f"Categoría {numero:02d}") for numero in range(11)]
        )
        listado = reverse("categoria-list")
        primera = self.client.get(listado, {"orden": "desc"})
        self.assertContains(primera, "Categoría 10")
        self.assertNotContains(primera, "Categoría 00")
        self.assertContains(primera, "page=2&amp;orden=desc")

        segunda = self.client.get(listado, {"page": 2, "orden": "desc"})
        self.assertContains(segunda, "Categoría 00")
        self.assertNotContains(segunda, "Categoría 10")
        self.assertContains(segunda, "page=1&amp;orden=desc")

    def test_busca_por_nombre_o_descripcion_a_la_izquierda_del_alta(self):
        for nombre, descripcion in (
            ("Servicios", "Mantenimiento"),
            ("Cliente", "Empresas que compran"),
            ("Alimentos", ""),
        ):
            Categoria.objects.create(nombre=nombre, descripcion=descripcion)
        listado = reverse("categoria-list")

        respuesta = self.client.get(listado, {"buscar": "  ali  "})
        html = respuesta.content.decode()
        self.assertLess(html.find('name="buscar"'), html.find("Nueva categoría"))
        self.assertContains(respuesta, 'aria-label="Buscar categoría"')
        self.assertContains(respuesta, 'placeholder="Buscar…"')
        self.assertContains(respuesta, 'value="ali"')
        self.assertContains(respuesta, "Alimentos")
        self.assertNotContains(respuesta, "Servicios")
        self.assertNotContains(respuesta, ">Cliente<")

        por_descripcion = self.client.get(listado, {"buscar": "manten"})
        self.assertContains(por_descripcion, "Servicios")
        self.assertNotContains(por_descripcion, "Alimentos")
        self.assertNotContains(por_descripcion, ">Cliente<")

        sin_coincidencias = self.client.get(listado, {"buscar": "zzz"})
        self.assertContains(sin_coincidencias, "Sin resultados")
        self.assertContains(sin_coincidencias, "«zzz»")
        self.assertNotContains(sin_coincidencias, "Todavía no hay categorías")

        ordenado = self.client.get(listado, {"buscar": "c", "orden": "desc"})
        self.assertRegex(
            ordenado.content.decode(),
            rf'class="table-sort desc"\s+href="{listado}\?buscar=c"',
        )
        self.assertContains(ordenado, "Servicios")
        self.assertContains(ordenado, "Cliente")
        self.assertNotContains(ordenado, "Alimentos")

    def test_la_busqueda_se_conserva_al_paginar(self):
        Categoria.objects.bulk_create(
            [Categoria(nombre=f"Categoría {numero:02d}") for numero in range(11)]
        )
        listado = reverse("categoria-list")
        primera = self.client.get(listado, {"buscar": "Categor", "orden": "desc"})
        self.assertContains(primera, "Categoría 10")
        self.assertNotContains(primera, "Categoría 00")
        self.assertContains(primera, "page=2&amp;orden=desc&amp;buscar=Categor")

        segunda = self.client.get(
            listado,
            {"page": 2, "orden": "desc", "buscar": "Categor"},
        )
        self.assertContains(segunda, "Categoría 00")
        self.assertNotContains(segunda, "Categoría 10")
        self.assertContains(segunda, "page=1&amp;orden=desc&amp;buscar=Categor")


class PruebasCrudEmpresa(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ana",
            password="clave-segura-1",
        )
        cls.otro_usuario = get_user_model().objects.create_user(
            username="bruno",
            password="clave-segura-2",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_las_pantallas_exigen_sesion(self):
        self.client.logout()
        for nombre in ("empresa-list", "empresa-crear"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("empresa-list"))
        self.assertContains(listado, 'id="modal-nueva-empresa"')
        self.assertContains(listado, 'data-bs-target="#modal-nueva-empresa"')
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("empresa-crear"))
        self.assertRedirects(alta, f"{reverse('empresa-list')}?nuevo=1")

    def test_crear_listar_editar_y_eliminar(self):
        categoria = Categoria.objects.create(nombre="Servicios")
        crear = self.client.post(
            reverse("empresa-crear"),
            {
                **_datos_empresa(),
                "email": "contacto@acme.test",
                "telefono": "021 123 456",
                "categorias": [str(categoria.pk)],
            },
            follow=True,
        )
        self.assertContains(crear, "Empresa creada.")
        empresa = Empresa.objects.get()
        self.assertEqual(empresa.razon_social, "Acme S.A.")
        self.assertEqual(empresa.ruc, RUC_VALIDO)
        self.assertEqual(empresa.email, "contacto@acme.test")
        self.assertEqual(empresa.usuario_creacion, self.usuario)
        self.assertEqual(empresa.usuario_modificacion, self.usuario)
        self.assertEqual(list(empresa.categorias.all()), [categoria])

        listado = self.client.get(reverse("empresa-list"))
        self.assertContains(listado, "Acme S.A.")
        self.assertContains(listado, 'id="modal-editar-empresa"')
        self.assertContains(listado, 'id="modal-eliminar-empresa"')

        self.client.force_login(self.otro_usuario)
        editar = self.client.post(
            reverse("empresa-editar", args=[empresa.pk]),
            {
                "razon_social": "Acme Paraguay S.A.",
                "ruc": RUC_VALIDO,
                "email": "ventas@acme.test",
                "telefono": "0981 000 111",
                "es_cliente": "on",
                "es_proveedor": "on",
                "activo": "on",
            },
            follow=True,
        )
        self.assertContains(editar, "Empresa actualizada.")
        empresa.refresh_from_db()
        self.assertEqual(empresa.razon_social, "Acme Paraguay S.A.")
        self.assertTrue(empresa.es_proveedor)
        self.assertEqual(empresa.usuario_creacion, self.usuario)
        self.assertEqual(empresa.usuario_modificacion, self.otro_usuario)

        self.client.post(
            reverse("empresa-eliminar", args=[empresa.pk]),
            follow=True,
        )
        self.assertFalse(Empresa.objects.exists())

    def test_guarda_ruc_sin_guion_tal_cual(self):
        respuesta = self.client.post(
            reverse("empresa-crear"),
            _datos_empresa(ruc="800123450"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Empresa.objects.get().ruc, "800123450")

    def test_rechaza_ruc_invalido_duplicado_y_razon_social_vacia(self):
        invalido = self.client.post(
            reverse("empresa-crear"),
            _datos_empresa(ruc="ABC"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(invalido.status_code, 400)
        self.assertIn(
            "Ingresá un RUC válido.",
            invalido.json()["errores"],
        )

        vacia = self.client.post(
            reverse("empresa-crear"),
            _datos_empresa(razon_social="   "),
        )
        self.assertContains(vacia, "La razón social no puede estar vacía.")
        self.assertContains(vacia, 'data-abrir="1"')

        _crear_empresa(self.usuario)
        duplicado = self.client.post(
            reverse("empresa-crear"),
            _datos_empresa(razon_social="Otra S.A."),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(duplicado.status_code, 400)
        self.assertEqual(
            duplicado.json()["errores"],
            ["Ya existe una empresa con ese RUC."],
        )

    def test_rechaza_sin_cliente_ni_proveedor_y_email_invalido(self):
        sin_tipo = self.client.post(
            reverse("empresa-crear"),
            {
                "razon_social": "Sin tipo S.A.",
                "ruc": "1234567-9",
                "activo": "on",
            },
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_tipo.status_code, 400)
        self.assertIn(
            "La empresa debe ser cliente, proveedor o ambas.",
            sin_tipo.json()["errores"],
        )

        email_invalido = self.client.post(
            reverse("empresa-crear"),
            _datos_empresa(email="correo-invalido"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(email_invalido.status_code, 400)
        self.assertIn("Ingresá un email válido.", email_invalido.json()["errores"])

    def test_busca_por_razon_social_ruc_o_email(self):
        _crear_empresa(
            self.usuario,
            razon_social="Distribuidora Norte",
            ruc="1234567-9",
            email="norte@test.com",
        )
        _crear_empresa(
            self.usuario,
            razon_social="Logística Sur",
            ruc="7654321-8",
            email="sur@test.com",
            es_cliente=True,
        )
        listado = reverse("empresa-list")

        por_razon = self.client.get(listado, {"buscar": "  norte  "})
        self.assertContains(por_razon, "Distribuidora Norte")
        self.assertNotContains(por_razon, "Logística Sur")
        self.assertContains(por_razon, 'value="norte"')

        por_ruc = self.client.get(listado, {"buscar": "7654321"})
        self.assertContains(por_ruc, "Logística Sur")
        self.assertNotContains(por_ruc, "Distribuidora Norte")

        por_email = self.client.get(listado, {"buscar": "sur@test"})
        self.assertContains(por_email, "Logística Sur")
        self.assertNotContains(por_email, "Distribuidora Norte")

    def test_filtra_por_cliente_proveedor_y_categoria(self):
        categoria_a = Categoria.objects.create(nombre="Alimentos")
        categoria_b = Categoria.objects.create(nombre="Servicios")
        cliente = _crear_empresa(
            self.usuario,
            razon_social="Solo Cliente",
            ruc="1234567-9",
            es_cliente=True,
            es_proveedor=False,
        )
        cliente.categorias.add(categoria_a)
        proveedor = _crear_empresa(
            self.usuario,
            razon_social="Solo Proveedor",
            ruc="2345678-9",
            es_cliente=False,
            es_proveedor=True,
        )
        proveedor.categorias.add(categoria_b)
        mixta = _crear_empresa(
            self.usuario,
            razon_social="Mixta",
            ruc="3456789-9",
            es_cliente=True,
            es_proveedor=True,
        )
        mixta.categorias.add(categoria_a, categoria_b)

        listado = reverse("empresa-list")
        solo_clientes = self.client.get(listado, {"cliente": "si"})
        self.assertContains(solo_clientes, "Solo Cliente")
        self.assertContains(solo_clientes, "Mixta")
        self.assertNotContains(solo_clientes, "Solo Proveedor")

        solo_proveedores = self.client.get(listado, {"proveedor": "si"})
        self.assertContains(solo_proveedores, "Solo Proveedor")
        self.assertContains(solo_proveedores, "Mixta")
        self.assertNotContains(solo_proveedores, "Solo Cliente")

        ambos = self.client.get(listado, {"cliente": "si", "proveedor": "si"})
        self.assertContains(ambos, "Mixta")
        self.assertNotContains(ambos, "Solo Cliente")
        self.assertNotContains(ambos, "Solo Proveedor")

        por_categoria = self.client.get(listado, {"categoria": str(categoria_a.pk)})
        self.assertContains(por_categoria, "Solo Cliente")
        self.assertContains(por_categoria, "Mixta")
        self.assertNotContains(por_categoria, "Solo Proveedor")

    def test_pagina_el_listado_y_conserva_filtros(self):
        for numero in range(11):
            _crear_empresa(
                self.usuario,
                razon_social=f"Empresa {numero:02d}",
                ruc=f"{1000000 + numero}-0",
            )
        listado = reverse("empresa-list")
        primera = self.client.get(listado, {"cliente": "si", "orden": "desc"})
        self.assertContains(primera, "Empresa 10")
        self.assertNotContains(primera, "Empresa 00")
        self.assertContains(
            primera,
            "page=2&amp;orden=desc&amp;columna=razon_social&amp;cliente=si",
        )

        segunda = self.client.get(
            listado,
            {"page": 2, "orden": "desc", "columna": "razon_social", "cliente": "si"},
        )
        self.assertContains(segunda, "Empresa 00")
        self.assertContains(
            segunda,
            "page=1&amp;orden=desc&amp;columna=razon_social&amp;cliente=si",
        )

    def test_la_cabecera_de_razon_social_recorre_ascendente_descendente_y_original(self):
        for razon_social in ("Servicios Globales", "Acme S.A.", "Beta Ltda."):
            _crear_empresa(
                self.usuario,
                razon_social=razon_social,
                ruc=f"{100000 + len(razon_social)}-0",
            )
        listado = reverse("empresa-list")

        def razones(respuesta):
            return re.findall(
                r"<tr>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        original = self.client.get(listado)
        self.assertEqual(
            razones(original),
            ["Acme S.A.", "Beta Ltda.", "Servicios Globales"],
        )
        ascendente = self.client.get(listado, {"orden": "asc", "columna": "razon_social"})
        self.assertEqual(
            razones(ascendente),
            ["Acme S.A.", "Beta Ltda.", "Servicios Globales"],
        )
        descendente = self.client.get(
            listado, {"orden": "desc", "columna": "razon_social"}
        )
        self.assertEqual(
            razones(descendente),
            ["Servicios Globales", "Beta Ltda.", "Acme S.A."],
        )


def _datos_contacto(empresa, **extra):
    datos = {
        "nombre": "Ana",
        "apellido": "Benítez",
        "empresa": str(empresa.pk),
        "email": "",
        "telefono": "",
        "cargo": "",
    }
    datos.update(extra)
    return datos


class PruebasCrudContacto(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ana",
            password="clave-segura-1",
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.empresa = _crear_empresa(self.usuario)

    def test_las_pantallas_exigen_sesion(self):
        self.client.logout()
        for nombre in ("contacto-list", "contacto-crear"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("contacto-list"))
        self.assertContains(listado, 'id="modal-nuevo-contacto"')
        self.assertContains(listado, 'data-bs-target="#modal-nuevo-contacto"')
        self.assertContains(listado, "tom-select.popular.min.js")
        self.assertContains(listado, "Indicá al menos un email o un teléfono.")
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("contacto-crear"))
        self.assertRedirects(alta, f"{reverse('contacto-list')}?nuevo=1")

    def test_el_menu_incluye_contactos(self):
        respuesta = self.client.get(reverse("empresa-list"))
        self.assertContains(respuesta, 'id="menu-principal"')
        self.assertContains(respuesta, "Contactos")
        self.assertContains(respuesta, reverse("contacto-list"))

    def test_crear_listar_editar_y_eliminar(self):
        crear = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(
                self.empresa,
                nombre="  Ana  ",
                apellido="  Benítez  ",
                email="ana@acme.test",
                telefono="021 111 222",
                cargo="  Compras  ",
            ),
            follow=True,
        )
        self.assertContains(crear, "Contacto creado.")
        contacto = Contacto.objects.get()
        self.assertEqual(contacto.nombre, "Ana")
        self.assertEqual(contacto.apellido, "Benítez")
        self.assertEqual(contacto.email, "ana@acme.test")
        self.assertEqual(contacto.telefono, "021 111 222")
        self.assertEqual(contacto.cargo, "Compras")
        self.assertEqual(contacto.empresa, self.empresa)

        listado = self.client.get(reverse("contacto-list"))
        self.assertContains(listado, "Ana")
        self.assertContains(listado, "Benítez")
        self.assertContains(listado, "Acme S.A.")
        self.assertContains(listado, 'id="modal-editar-contacto"')
        self.assertContains(listado, 'id="modal-eliminar-contacto"')
        self.assertContains(listado, f'data-empresa="{self.empresa.pk}"')
        self.assertNotContains(
            listado,
            f'href="{reverse("contacto-editar", args=[contacto.pk])}"',
        )

        edicion = self.client.get(reverse("contacto-editar", args=[contacto.pk]))
        self.assertRedirects(edicion, reverse("contacto-list"))

        confirmacion = self.client.get(
            reverse("contacto-eliminar", args=[contacto.pk])
        )
        self.assertRedirects(confirmacion, reverse("contacto-list"))

        otra = _crear_empresa(
            self.usuario,
            razon_social="Otra S.A.",
            ruc="1234567-9",
        )
        editar = self.client.post(
            reverse("contacto-editar", args=[contacto.pk]),
            _datos_contacto(
                otra,
                nombre="Bruno",
                apellido="Gómez",
                email="bruno@otra.test",
                telefono="0981 000 111",
                cargo="Ventas",
            ),
            follow=True,
        )
        self.assertContains(editar, "Contacto actualizado.")
        contacto.refresh_from_db()
        self.assertEqual(contacto.nombre, "Bruno")
        self.assertEqual(contacto.apellido, "Gómez")
        self.assertEqual(contacto.empresa, otra)
        self.assertEqual(contacto.cargo, "Ventas")

        self.client.post(
            reverse("contacto-eliminar", args=[contacto.pk]),
            follow=True,
        )
        self.assertFalse(Contacto.objects.exists())

    def test_rechaza_datos_vacios_email_invalido_y_sin_empresa(self):
        vacio = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(self.empresa, nombre="   ", apellido="   "),
        )
        self.assertContains(vacio, "El nombre no puede estar vacío.")
        self.assertContains(vacio, "El apellido no puede estar vacío.")
        self.assertContains(vacio, 'data-bs-delay="10000"')
        self.assertContains(vacio, 'data-abrir="1"')
        self.assertContains(vacio, "is-invalid")
        self.assertFalse(Contacto.objects.exists())

        sin_empresa = self.client.post(
            reverse("contacto-crear"),
            {
                "nombre": "Ana",
                "apellido": "Benítez",
                "email": "ana@acme.test",
                "telefono": "",
                "cargo": "",
            },
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_empresa.status_code, 400)
        self.assertEqual(sin_empresa.json()["errores"], ["Seleccioná una empresa."])
        self.assertEqual(sin_empresa.json()["campos"], ["empresa"])

        email_invalido = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(self.empresa, email="correo-invalido"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(email_invalido.status_code, 400)
        self.assertIn("Ingresá un email válido.", email_invalido.json()["errores"])

        telefono_largo = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(self.empresa, telefono="1" * 31),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(telefono_largo.status_code, 400)
        self.assertEqual(
            telefono_largo.json()["errores"],
            ["El teléfono no puede superar los 30 caracteres."],
        )
        self.assertFalse(Contacto.objects.exists())

        contacto = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
        )
        edicion_vacia = self.client.post(
            reverse("contacto-editar", args=[contacto.pk]),
            _datos_contacto(self.empresa, apellido="   ", email="ana@acme.test"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_vacia.status_code, 400)
        self.assertEqual(
            edicion_vacia.json()["errores"],
            ["El apellido no puede estar vacío."],
        )
        contacto.refresh_from_db()
        self.assertEqual(contacto.apellido, "Benítez")

    def test_exige_email_o_telefono(self):
        sin_medio = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(self.empresa, email="   ", telefono="   "),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_medio.status_code, 400)
        self.assertEqual(
            sin_medio.json()["errores"],
            ["Indicá un email o un teléfono."],
        )
        self.assertCountEqual(
            sin_medio.json()["campos"],
            ["email", "telefono"],
        )
        self.assertFalse(Contacto.objects.exists())

        solo_email = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(self.empresa, email="ana@acme.test"),
            follow=True,
        )
        self.assertContains(solo_email, "Contacto creado.")
        contacto = Contacto.objects.get(email="ana@acme.test")
        self.assertEqual(contacto.telefono, "")

        solo_telefono = self.client.post(
            reverse("contacto-crear"),
            _datos_contacto(
                self.empresa,
                nombre="Bruno",
                apellido="Gómez",
                telefono="0981 000 111",
            ),
            follow=True,
        )
        self.assertContains(solo_telefono, "Contacto creado.")
        por_telefono = Contacto.objects.get(telefono="0981 000 111")
        self.assertEqual(por_telefono.email, "")

        sin_medio_al_editar = self.client.post(
            reverse("contacto-editar", args=[contacto.pk]),
            _datos_contacto(self.empresa, email="", telefono=""),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_medio_al_editar.status_code, 400)
        self.assertEqual(
            sin_medio_al_editar.json()["errores"],
            ["Indicá un email o un teléfono."],
        )
        contacto.refresh_from_db()
        self.assertEqual(contacto.email, "ana@acme.test")

    def test_el_modelo_exige_email_o_telefono(self):
        with self.assertRaises(ValidationError):
            Contacto.objects.create(
                empresa=self.empresa,
                nombre="Ana",
                apellido="Benítez",
                email="   ",
                telefono="  ",
            )
        self.assertFalse(Contacto.objects.exists())

        contacto = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            telefono="021 111 222",
        )
        self.assertEqual(contacto.email, "")
        contacto.telefono = ""
        contacto.email = "ana@acme.test"
        contacto.save()
        contacto.refresh_from_db()
        self.assertEqual(contacto.email, "ana@acme.test")
        self.assertEqual(contacto.telefono, "")

        with self.assertRaises(IntegrityError):
            Contacto.objects.bulk_create(
                [
                    Contacto(
                        empresa=self.empresa,
                        nombre="Carla",
                        apellido="Alvarez",
                    )
                ]
            )

    def test_el_modelo_rechaza_nombre_y_apellido_vacios(self):
        with self.assertRaises(ValidationError):
            Contacto.objects.create(
                empresa=self.empresa,
                nombre="   ",
                apellido="Benítez",
            )
        with self.assertRaises(ValidationError):
            Contacto.objects.create(
                empresa=self.empresa,
                nombre="Ana",
                apellido="   ",
            )

    def test_eliminar_la_empresa_elimina_sus_contactos(self):
        Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
        )
        self.client.post(
            reverse("empresa-eliminar", args=[self.empresa.pk]),
            follow=True,
        )
        self.assertFalse(Empresa.objects.filter(pk=self.empresa.pk).exists())
        self.assertFalse(Contacto.objects.exists())

    def test_busca_por_nombre_apellido_email_cargo_telefono_o_empresa(self):
        otra = _crear_empresa(
            self.usuario,
            razon_social="Logística Sur",
            ruc="1234567-9",
        )
        Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
            telefono="021 111",
            cargo="Compras",
        )
        Contacto.objects.create(
            empresa=otra,
            nombre="Bruno",
            apellido="Gómez",
            email="bruno@sur.test",
            telefono="0981 222",
            cargo="Ventas",
        )
        listado = reverse("contacto-list")

        por_nombre = self.client.get(listado, {"buscar": "  ana  "})
        html = por_nombre.content.decode()
        self.assertLess(html.find('name="buscar"'), html.find("Nuevo contacto"))
        self.assertContains(por_nombre, 'aria-label="Buscar contacto"')
        self.assertContains(por_nombre, 'value="ana"')
        self.assertContains(por_nombre, "Benítez")
        self.assertNotContains(por_nombre, "Gómez")

        por_apellido = self.client.get(listado, {"buscar": "gómez"})
        self.assertContains(por_apellido, "Bruno")
        self.assertNotContains(por_apellido, "Benítez")

        por_email = self.client.get(listado, {"buscar": "ana@acme"})
        self.assertContains(por_email, "Benítez")
        self.assertNotContains(por_email, "Gómez")

        por_cargo = self.client.get(listado, {"buscar": "ventas"})
        self.assertContains(por_cargo, "Gómez")
        self.assertNotContains(por_cargo, "Benítez")

        por_telefono = self.client.get(listado, {"buscar": "021"})
        self.assertContains(por_telefono, "Benítez")
        self.assertNotContains(por_telefono, "Gómez")

        por_empresa = self.client.get(listado, {"buscar": "logística"})
        self.assertContains(por_empresa, "Gómez")
        self.assertNotContains(por_empresa, "Benítez")

        sin_coincidencias = self.client.get(listado, {"buscar": "zzz"})
        self.assertContains(sin_coincidencias, "Sin resultados")
        self.assertNotContains(sin_coincidencias, "Todavía no hay contactos")

    def test_filtra_por_empresa(self):
        otra = _crear_empresa(
            self.usuario,
            razon_social="Logística Sur",
            ruc="1234567-9",
        )
        Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
        )
        Contacto.objects.create(
            empresa=otra,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 222",
        )
        listado = reverse("contacto-list")
        filtrado = self.client.get(listado, {"empresa": str(otra.pk)})
        self.assertContains(filtrado, "Gómez")
        self.assertNotContains(filtrado, "Benítez")
        self.assertContains(filtrado, "Todas las empresas")

    def test_pagina_el_listado_y_conserva_filtros(self):
        Contacto.objects.bulk_create(
            [
                Contacto(
                    empresa=self.empresa,
                    nombre=f"Nombre {numero:02d}",
                    apellido="Pérez",
                    email=f"contacto{numero:02d}@acme.test",
                )
                for numero in range(11)
            ]
        )
        listado = reverse("contacto-list")
        primera = self.client.get(
            listado,
            {"empresa": str(self.empresa.pk), "orden": "desc", "columna": "nombre"},
        )
        self.assertContains(primera, "Nombre 10")
        self.assertNotContains(primera, "Nombre 00")
        self.assertContains(
            primera,
            f"page=2&amp;orden=desc&amp;columna=nombre&amp;empresa={self.empresa.pk}",
        )

        segunda = self.client.get(
            listado,
            {
                "page": 2,
                "orden": "desc",
                "columna": "nombre",
                "empresa": str(self.empresa.pk),
            },
        )
        self.assertContains(segunda, "Nombre 00")
        self.assertContains(
            segunda,
            f"page=1&amp;orden=desc&amp;columna=nombre&amp;empresa={self.empresa.pk}",
        )

    def test_la_cabecera_de_apellido_recorre_ascendente_descendente_y_original(self):
        for nombre, apellido in (
            ("Bruno", "Gomez"),
            ("Ana", "Benitez"),
            ("Carla", "Alvarez"),
        ):
            Contacto.objects.create(
                empresa=self.empresa,
                nombre=nombre,
                apellido=apellido,
                email=f"{nombre.lower()}@acme.test",
            )
        listado = reverse("contacto-list")

        def apellidos(respuesta):
            return re.findall(
                r"<tr>\s*<td>[^<]+</td>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        original = self.client.get(listado)
        self.assertEqual(apellidos(original), ["Alvarez", "Benitez", "Gomez"])
        self.assertContains(original, 'aria-sort="none"')
        self.assertContains(original, 'aria-label="Ordenar por apellido ascendente"')

        ascendente = self.client.get(listado, {"orden": "asc", "columna": "apellido"})
        self.assertEqual(apellidos(ascendente), ["Alvarez", "Benitez", "Gomez"])
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-label="Ordenar por apellido descendente"')

        descendente = self.client.get(listado, {"orden": "desc", "columna": "apellido"})
        self.assertEqual(apellidos(descendente), ["Gomez", "Benitez", "Alvarez"])
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')

    def test_la_cabecera_de_empresa_recorre_ascendente_descendente_y_original(self):
        otra = _crear_empresa(
            self.usuario,
            razon_social="Logística Sur",
            ruc="1234567-9",
        )
        Contacto.objects.create(
            empresa=otra,
            nombre="Bruno",
            apellido="Gómez",
            email="bruno@sur.test",
        )
        Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
        )
        listado = reverse("contacto-list")

        def empresas(respuesta):
            return re.findall(
                r"<tr>\s*<td>[^<]+</td>\s*<td>[^<]+</td>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        ascendente = self.client.get(listado, {"orden": "asc", "columna": "empresa"})
        self.assertEqual(empresas(ascendente), ["Acme S.A.", "Logística Sur"])
        self.assertContains(ascendente, 'aria-label="Ordenar por empresa descendente"')
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=empresa"',
        )

        descendente = self.client.get(listado, {"orden": "desc", "columna": "empresa"})
        self.assertEqual(empresas(descendente), ["Logística Sur", "Acme S.A."])
        self.assertContains(descendente, 'aria-label="Volver al orden original"')

    def test_sin_empresas_pide_crear_una(self):
        self.empresa.delete()
        listado = self.client.get(reverse("contacto-list"))
        self.assertContains(listado, "Todavía no hay contactos")
        self.assertContains(listado, "Primero creá una empresa")
        self.assertContains(listado, reverse("empresa-list"))


def _datos_direccion(contacto, ciudad, **extra):
    datos = {
        "direccion": "Av. España 123",
        "tipo": "Laboral",
        "codigo_postal": "",
        "contacto": str(contacto.pk),
        "ciudad": str(ciudad.pk),
    }
    datos.update(extra)
    return datos


class PruebasCrudDireccion(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ana",
            password="clave-segura-1",
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.departamento = Departamento.objects.create(nombre="Central")
        self.ciudad = Ciudad.objects.create(
            nombre="Asunción",
            departamento=self.departamento,
        )
        self.otra_ciudad = Ciudad.objects.create(
            nombre="Lambaré",
            departamento=self.departamento,
        )
        self.empresa = _crear_empresa(self.usuario)
        self.contacto = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Ana",
            apellido="Benítez",
            email="ana@acme.test",
        )

    def test_las_pantallas_exigen_sesion(self):
        self.client.logout()
        for nombre in ("direccion-list", "direccion-crear"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("login"), respuesta.url)

    def test_el_alta_esta_en_un_modal(self):
        listado = self.client.get(reverse("direccion-list"))
        self.assertContains(listado, 'id="modal-nueva-direccion"')
        self.assertContains(listado, 'data-bs-target="#modal-nueva-direccion"')
        self.assertContains(listado, "tom-select.popular.min.js")
        self.assertContains(listado, "Opcional.")
        self.assertNotContains(listado, 'data-abrir="1"')

        alta = self.client.get(reverse("direccion-crear"))
        self.assertRedirects(alta, f"{reverse('direccion-list')}?nuevo=1")

    def test_el_menu_incluye_direcciones(self):
        respuesta = self.client.get(reverse("empresa-list"))
        self.assertContains(respuesta, 'id="menu-principal"')
        self.assertContains(respuesta, "Direcciones")
        self.assertContains(respuesta, reverse("direccion-list"))

    def test_crear_listar_editar_y_eliminar(self):
        crear = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(
                self.contacto,
                self.ciudad,
                direccion="  Av. España 123  ",
                tipo="  Laboral  ",
                codigo_postal="  1209  ",
            ),
            follow=True,
        )
        self.assertContains(crear, "Dirección creada.")
        direccion = Direccion.objects.get()
        self.assertEqual(direccion.direccion, "Av. España 123")
        self.assertEqual(direccion.tipo, "Laboral")
        self.assertEqual(direccion.codigo_postal, "1209")
        self.assertEqual(direccion.contacto, self.contacto)
        self.assertEqual(direccion.ciudad, self.ciudad)

        listado = self.client.get(reverse("direccion-list"))
        self.assertContains(listado, "Av. España 123")
        self.assertContains(listado, "Ana Benítez")
        self.assertContains(listado, "Asunción")
        self.assertContains(listado, 'id="modal-editar-direccion"')
        self.assertContains(listado, 'id="modal-eliminar-direccion"')
        self.assertContains(listado, f'data-contacto="{self.contacto.pk}"')
        self.assertContains(listado, f'data-ciudad="{self.ciudad.pk}"')
        self.assertNotContains(
            listado,
            f'href="{reverse("direccion-editar", args=[direccion.pk])}"',
        )

        edicion = self.client.get(reverse("direccion-editar", args=[direccion.pk]))
        self.assertRedirects(edicion, reverse("direccion-list"))

        confirmacion = self.client.get(
            reverse("direccion-eliminar", args=[direccion.pk])
        )
        self.assertRedirects(confirmacion, reverse("direccion-list"))

        otro = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 000 111",
        )
        editar = self.client.post(
            reverse("direccion-editar", args=[direccion.pk]),
            _datos_direccion(
                otro,
                self.otra_ciudad,
                direccion="Calle Palma 50",
                tipo="Particular",
                codigo_postal="001",
            ),
            follow=True,
        )
        self.assertContains(editar, "Dirección actualizada.")
        direccion.refresh_from_db()
        self.assertEqual(direccion.direccion, "Calle Palma 50")
        self.assertEqual(direccion.tipo, "Particular")
        self.assertEqual(direccion.codigo_postal, "001")
        self.assertEqual(direccion.contacto, otro)
        self.assertEqual(direccion.ciudad, self.otra_ciudad)

        self.client.post(
            reverse("direccion-eliminar", args=[direccion.pk]),
            follow=True,
        )
        self.assertFalse(Direccion.objects.exists())

    def test_rechaza_datos_vacios_largos_y_sin_relaciones(self):
        vacio = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(self.contacto, self.ciudad, direccion="   ", tipo="   "),
        )
        self.assertContains(vacio, "La dirección no puede estar vacía.")
        self.assertContains(vacio, "El tipo no puede estar vacío.")
        self.assertContains(vacio, 'data-bs-delay="10000"')
        self.assertContains(vacio, 'data-abrir="1"')
        self.assertContains(vacio, "is-invalid")
        self.assertFalse(Direccion.objects.exists())

        sin_relaciones = self.client.post(
            reverse("direccion-crear"),
            {
                "direccion": "Av. España 123",
                "tipo": "Laboral",
                "codigo_postal": "",
            },
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(sin_relaciones.status_code, 400)
        self.assertIn("Seleccioná un contacto.", sin_relaciones.json()["errores"])
        self.assertIn("Seleccioná una ciudad.", sin_relaciones.json()["errores"])
        self.assertCountEqual(sin_relaciones.json()["campos"], ["contacto", "ciudad"])

        postal_largo = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(self.contacto, self.ciudad, codigo_postal="1" * 21),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(postal_largo.status_code, 400)
        self.assertEqual(
            postal_largo.json()["errores"],
            ["El código postal no puede superar los 20 caracteres."],
        )
        self.assertEqual(postal_largo.json()["campos"], ["codigo_postal"])

        direccion_larga = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(self.contacto, self.ciudad, direccion="a" * 256),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(direccion_larga.status_code, 400)
        self.assertEqual(
            direccion_larga.json()["errores"],
            ["La dirección no puede superar los 255 caracteres."],
        )
        self.assertFalse(Direccion.objects.exists())

        direccion = Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        edicion_vacia = self.client.post(
            reverse("direccion-editar", args=[direccion.pk]),
            _datos_direccion(self.contacto, self.ciudad, tipo="   "),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_vacia.status_code, 400)
        self.assertEqual(
            edicion_vacia.json()["errores"],
            ["El tipo no puede estar vacío."],
        )
        direccion.refresh_from_db()
        self.assertEqual(direccion.tipo, "Laboral")

    def test_rechaza_direccion_repetida_en_el_mismo_contacto_y_ciudad(self):
        mensaje = "Ya existe esa dirección para ese contacto en esa ciudad."
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        duplicado = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(self.contacto, self.ciudad, tipo="Particular"),
        )
        self.assertContains(duplicado, mensaje)
        self.assertEqual(Direccion.objects.count(), 1)

        otra_mayuscula = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(
                self.contacto,
                self.ciudad,
                direccion="  av. españa 123  ",
                tipo="Comercial",
                codigo_postal="9999",
            ),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otra_mayuscula.status_code, 400)
        self.assertEqual(otra_mayuscula.json()["errores"], [mensaje])
        self.assertIn("direccion", otra_mayuscula.json()["campos"])
        self.assertEqual(Direccion.objects.count(), 1)

        otra_ciudad = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(self.contacto, self.otra_ciudad),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otra_ciudad.status_code, 200)
        self.assertEqual(Direccion.objects.count(), 2)

        otro = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 000 111",
        )
        otro_contacto = self.client.post(
            reverse("direccion-crear"),
            _datos_direccion(otro, self.ciudad),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(otro_contacto.status_code, 200)
        self.assertEqual(Direccion.objects.count(), 3)

        repetida = Direccion.objects.get(ciudad=self.otra_ciudad)
        edicion_duplicada = self.client.post(
            reverse("direccion-editar", args=[repetida.pk]),
            _datos_direccion(self.contacto, self.ciudad, direccion="AV. ESPAÑA 123"),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion_duplicada.status_code, 400)
        self.assertEqual(edicion_duplicada.json()["errores"], [mensaje])
        repetida.refresh_from_db()
        self.assertEqual(repetida.direccion, "Av. España 123")
        self.assertEqual(repetida.ciudad, self.otra_ciudad)

        original = Direccion.objects.get(contacto=self.contacto, ciudad=self.ciudad)
        edicion = self.client.post(
            reverse("direccion-editar", args=[original.pk]),
            _datos_direccion(
                self.contacto,
                self.ciudad,
                tipo="Comercial",
                codigo_postal="1209",
            ),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(edicion.status_code, 200)
        original.refresh_from_db()
        self.assertEqual(original.tipo, "Comercial")
        self.assertEqual(original.codigo_postal, "1209")

        with self.assertRaises(ValidationError) as contexto:
            Direccion.objects.create(
                contacto=self.contacto,
                ciudad=self.ciudad,
                direccion="av. españa 123",
                tipo="Particular",
            )
        self.assertIn(mensaje, contexto.exception.message_dict["direccion"])

        with self.assertRaises(IntegrityError):
            Direccion.objects.bulk_create(
                [
                    Direccion(
                        contacto=self.contacto,
                        ciudad=self.ciudad,
                        direccion="AV. ESPAÑA 123",
                        tipo="Particular",
                    )
                ]
            )

    def test_el_modelo_rechaza_direccion_y_tipo_vacios(self):
        with self.assertRaises(ValidationError):
            Direccion.objects.create(
                contacto=self.contacto,
                ciudad=self.ciudad,
                direccion="   ",
                tipo="Laboral",
            )
        with self.assertRaises(ValidationError):
            Direccion.objects.create(
                contacto=self.contacto,
                ciudad=self.ciudad,
                direccion="Av. España 123",
                tipo="   ",
            )
        self.assertFalse(Direccion.objects.exists())

        direccion = Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
            codigo_postal="  ",
        )
        self.assertEqual(direccion.codigo_postal, "")

        with self.assertRaises(IntegrityError):
            Direccion.objects.bulk_create(
                [
                    Direccion(
                        contacto=self.contacto,
                        ciudad=self.ciudad,
                        direccion="   ",
                        tipo="Laboral",
                    )
                ]
            )

    def test_busca_por_direccion_tipo_postal_contacto_empresa_o_ciudad(self):
        otra_empresa = _crear_empresa(
            self.usuario,
            razon_social="Logística Sur",
            ruc="1234567-9",
        )
        otro = Contacto.objects.create(
            empresa=otra_empresa,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 222",
        )
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
            codigo_postal="1209",
        )
        Direccion.objects.create(
            contacto=otro,
            ciudad=self.otra_ciudad,
            direccion="Calle Palma 50",
            tipo="Particular",
            codigo_postal="001",
        )
        listado = reverse("direccion-list")

        por_direccion = self.client.get(listado, {"buscar": "  españa  "})
        html = por_direccion.content.decode()
        self.assertLess(html.find('name="buscar"'), html.find("Nueva dirección"))
        self.assertContains(por_direccion, 'aria-label="Buscar dirección"')
        self.assertContains(por_direccion, 'value="españa"')
        self.assertContains(por_direccion, "Av. España 123")
        self.assertNotContains(por_direccion, "Calle Palma 50")

        por_tipo = self.client.get(listado, {"buscar": "particular"})
        self.assertContains(por_tipo, "Calle Palma 50")
        self.assertNotContains(por_tipo, "Av. España 123")

        por_postal = self.client.get(listado, {"buscar": "1209"})
        self.assertContains(por_postal, "Av. España 123")
        self.assertNotContains(por_postal, "Calle Palma 50")

        por_contacto = self.client.get(listado, {"buscar": "gómez"})
        self.assertContains(por_contacto, "Calle Palma 50")
        self.assertNotContains(por_contacto, "Av. España 123")

        por_empresa = self.client.get(listado, {"buscar": "logística"})
        self.assertContains(por_empresa, "Calle Palma 50")
        self.assertNotContains(por_empresa, "Av. España 123")

        por_ciudad = self.client.get(listado, {"buscar": "lambaré"})
        self.assertContains(por_ciudad, "Calle Palma 50")
        self.assertNotContains(por_ciudad, "Av. España 123")

        sin_coincidencias = self.client.get(listado, {"buscar": "zzz"})
        self.assertContains(sin_coincidencias, "Sin resultados")
        self.assertNotContains(sin_coincidencias, "Todavía no hay direcciones")

    def test_filtra_por_contacto_y_ciudad(self):
        otro = Contacto.objects.create(
            empresa=self.empresa,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 222",
        )
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        Direccion.objects.create(
            contacto=otro,
            ciudad=self.otra_ciudad,
            direccion="Calle Palma 50",
            tipo="Particular",
        )
        listado = reverse("direccion-list")

        por_contacto = self.client.get(listado, {"contacto": str(otro.pk)})
        self.assertContains(por_contacto, "Calle Palma 50")
        self.assertNotContains(por_contacto, "Av. España 123")
        self.assertContains(por_contacto, "Todos los contactos")

        por_ciudad = self.client.get(listado, {"ciudad": str(self.ciudad.pk)})
        self.assertContains(por_ciudad, "Av. España 123")
        self.assertNotContains(por_ciudad, "Calle Palma 50")
        self.assertContains(por_ciudad, "Todas las ciudades")

        ambos = self.client.get(
            listado,
            {"contacto": str(self.contacto.pk), "ciudad": str(self.otra_ciudad.pk)},
        )
        self.assertContains(ambos, "Sin resultados")
        self.assertNotContains(ambos, "Av. España 123")
        self.assertNotContains(ambos, "Calle Palma 50")

    def test_pagina_el_listado_y_conserva_filtros(self):
        Direccion.objects.bulk_create(
            [
                Direccion(
                    contacto=self.contacto,
                    ciudad=self.ciudad,
                    direccion=f"Calle {numero:02d}",
                    tipo="Laboral",
                )
                for numero in range(11)
            ]
        )
        listado = reverse("direccion-list")
        primera = self.client.get(
            listado,
            {
                "contacto": str(self.contacto.pk),
                "orden": "desc",
                "columna": "direccion",
            },
        )
        self.assertContains(primera, "Calle 10")
        self.assertNotContains(primera, "Calle 00")
        self.assertContains(
            primera,
            f"page=2&amp;orden=desc&amp;columna=direccion&amp;contacto={self.contacto.pk}",
        )

        segunda = self.client.get(
            listado,
            {
                "page": 2,
                "orden": "desc",
                "columna": "direccion",
                "contacto": str(self.contacto.pk),
            },
        )
        self.assertContains(segunda, "Calle 00")
        self.assertContains(
            segunda,
            f"page=1&amp;orden=desc&amp;columna=direccion&amp;contacto={self.contacto.pk}",
        )

    def test_la_cabecera_de_direccion_recorre_ascendente_descendente_y_original(self):
        for texto in ("Calle Palma", "Av. España", "Brasilia 100"):
            Direccion.objects.create(
                contacto=self.contacto,
                ciudad=self.ciudad,
                direccion=texto,
                tipo="Laboral",
            )
        listado = reverse("direccion-list")

        def textos(respuesta):
            return re.findall(
                r"<tr>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        original = self.client.get(listado)
        self.assertEqual(
            textos(original),
            ["Av. España", "Brasilia 100", "Calle Palma"],
        )
        self.assertContains(original, 'aria-sort="none"')
        self.assertContains(original, 'aria-label="Ordenar por dirección ascendente"')

        ascendente = self.client.get(listado, {"orden": "asc", "columna": "direccion"})
        self.assertEqual(
            textos(ascendente),
            ["Av. España", "Brasilia 100", "Calle Palma"],
        )
        self.assertContains(ascendente, 'aria-sort="ascending"')
        self.assertContains(ascendente, 'aria-label="Ordenar por dirección descendente"')

        descendente = self.client.get(
            listado, {"orden": "desc", "columna": "direccion"}
        )
        self.assertEqual(
            textos(descendente),
            ["Calle Palma", "Brasilia 100", "Av. España"],
        )
        self.assertContains(descendente, 'aria-sort="descending"')
        self.assertContains(descendente, 'aria-label="Volver al orden original"')

    def test_la_cabecera_de_ciudad_recorre_ascendente_descendente_y_original(self):
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.otra_ciudad,
            direccion="Calle Palma 50",
            tipo="Particular",
        )
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        listado = reverse("direccion-list")

        def ciudades(respuesta):
            return re.findall(
                r"<tr>\s*<td>[^<]+</td>\s*<td>[^<]+</td>\s*<td>.*?</td>\s*<td>[^<]+</td>\s*<td>([^<]+)</td>",
                respuesta.content.decode(),
            )

        ascendente = self.client.get(listado, {"orden": "asc", "columna": "ciudad"})
        self.assertEqual(ciudades(ascendente), ["Asunción", "Lambaré"])
        self.assertContains(ascendente, 'aria-label="Ordenar por ciudad descendente"')
        self.assertRegex(
            ascendente.content.decode(),
            rf'class="table-sort asc"\s+href="{listado}\?orden=desc&amp;columna=ciudad"',
        )

        descendente = self.client.get(listado, {"orden": "desc", "columna": "ciudad"})
        self.assertEqual(ciudades(descendente), ["Lambaré", "Asunción"])
        self.assertContains(descendente, 'aria-label="Volver al orden original"')

    def test_eliminar_el_contacto_elimina_sus_direcciones(self):
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        self.client.post(
            reverse("contacto-eliminar", args=[self.contacto.pk]),
            follow=True,
        )
        self.assertFalse(Contacto.objects.filter(pk=self.contacto.pk).exists())
        self.assertFalse(Direccion.objects.exists())

    def test_no_se_elimina_una_ciudad_con_direcciones(self):
        Direccion.objects.create(
            contacto=self.contacto,
            ciudad=self.ciudad,
            direccion="Av. España 123",
            tipo="Laboral",
        )
        respuesta = self.client.post(
            reverse("ciudad-eliminar", args=[self.ciudad.pk]),
            headers={"X-Solicitud": "fetch"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["errores"],
            ["No se puede eliminar la ciudad porque tiene direcciones asociadas."],
        )
        self.assertTrue(Ciudad.objects.filter(pk=self.ciudad.pk).exists())
        self.assertTrue(Direccion.objects.exists())

    def test_sin_contacto_o_ciudad_pide_crearlos(self):
        self.contacto.delete()
        sin_contacto = self.client.get(reverse("direccion-list"))
        self.assertContains(sin_contacto, "Todavía no hay direcciones")
        self.assertContains(sin_contacto, "Primero creá un contacto")
        self.assertContains(sin_contacto, reverse("contacto-list"))

        self.ciudad.delete()
        self.otra_ciudad.delete()
        sin_ambos = self.client.get(reverse("direccion-list"))
        self.assertContains(sin_ambos, "Primero creá un contacto y una ciudad.")
        self.assertContains(sin_ambos, reverse("ciudad-list"))

        Contacto.objects.create(
            empresa=self.empresa,
            nombre="Bruno",
            apellido="Gómez",
            telefono="0981 222",
        )
        sin_ciudad = self.client.get(reverse("direccion-list"))
        self.assertContains(sin_ciudad, "Primero creá una ciudad")
        self.assertContains(sin_ciudad, reverse("ciudad-list"))
