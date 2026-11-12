"""Pruebas de reglas de negocio y de recuperación ante errores."""
import unittest
from decimal import Decimal
from main import (Sistema, Sala, Equipo, Asesoria, Estado, DatosInvalidos,
                  OperacionNoPermitida, Entidad, Servicio)


class PruebasSistema(unittest.TestCase):
    def setUp(self):
        self.s = Sistema()
        self.s.registrar_cliente('C1', 'Ana', 'ana@example.com', '3001234567')
        self.s.registrar_servicio('sala', 'S1', 'Sala', 50000, 10)

    def test_abstraccion(self):
        for clase in (Entidad, Servicio):
            with self.assertRaises(TypeError):
                clase('X')

    def test_costos_polimorficos(self):
        servicios = [Sala('S', 'Sala', 50000, 5),
                     Equipo('E', 'Equipo', 20000, 5000),
                     Asesoria('A', 'Asesoría', 80000, 'Python')]
        self.assertEqual([s.calcular_costo(4) for s in servicios],
                         [Decimal('200000'), Decimal('85000'), Decimal('288000')])
        self.assertEqual(servicios[0].calcular_costo(2, '0.19', '0.10'), Decimal('107100.00'))

    def test_no_registra_cliente_invalido_o_duplicado(self):
        for datos in [('C2', 'Luis', 'mal', '3001234567'),
                      ('C1', 'Ana', 'ana@example.com', '3001234567')]:
            with self.assertRaises(DatosInvalidos):
                self.s.registrar_cliente(*datos)
        self.assertEqual(len(self.s.clientes), 1)

    def test_rechaza_no_finitos_y_booleanos(self):
        for valor in ('NaN', 'Infinity', True, -1, 0):
            with self.subTest(valor=valor), self.assertRaises(DatosInvalidos):
                self.s.servicios[0].calcular_costo(valor)

    def test_error_de_calculo_preserva_reserva_y_encadena_causa(self):
        r = self.s.crear_reserva('R1', 'C1', 'S1', 2)
        r.confirmar()
        with self.assertRaises(OperacionNoPermitida) as contexto:
            r.procesar(descuento=2)
        self.assertIsInstance(contexto.exception.__cause__, DatosInvalidos)
        self.assertEqual(r.estado, Estado.CONFIRMADA)
        self.assertIsNone(r.total)
        self.assertFalse(self.s.servicios[0].disponible)
        self.assertEqual(r.procesar(), Decimal('100000.00'))
        self.assertTrue(self.s.servicios[0].disponible)

    def test_conflicto_entre_reservas_pendientes(self):
        r1 = self.s.crear_reserva('R1', 'C1', 'S1', 2)
        r2 = self.s.crear_reserva('R2', 'C1', 'S1', 2)
        r1.confirmar()
        with self.assertRaises(OperacionNoPermitida):
            r2.confirmar()
        r2.cancelar()
        self.assertFalse(self.s.servicios[0].disponible)
        r1.cancelar()
        self.assertTrue(self.s.servicios[0].disponible)
        with self.assertRaises(OperacionNoPermitida):
            r1.confirmar()


if __name__ == '__main__':
    unittest.main()
