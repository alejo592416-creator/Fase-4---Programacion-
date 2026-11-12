"""Sistema académico Software FJ"""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
import argparse
import logging
import re

class ErrorSistema(Exception):
    """Error de negocio que puede mostrarse al usuario."""

class DatosInvalidos(ErrorSistema):
    pass

class NoEncontrado(ErrorSistema):
    pass

class OperacionNoPermitida(ErrorSistema):
    pass

def texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise DatosInvalidos(f"{campo}: se requiere texto no vacío.")
    return valor.strip()

def numero(valor, campo, minimo=Decimal('0'), maximo=None):
    try:
        if isinstance(valor, bool):
            raise ValueError('Un booleano no es un número válido.')
        resultado = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as causa:
        raise DatosInvalidos(f"{campo}: debe ser un número válido.") from causa
    if not resultado.is_finite() or resultado < minimo:
        raise DatosInvalidos(f"{campo}: debe ser finito y mayor o igual a {minimo}.")
    if maximo is not None and resultado > maximo:
        raise DatosInvalidos(f"{campo}: no puede superar {maximo}.")
    return resultado


class Entidad(ABC):
    def __init__(self, identificador):
        self.__identificador = texto(identificador, 'Identificador')

    @property
    def identificador(self):
        return self.__identificador

    @abstractmethod
    def describir(self):
        """Devuelve una descripción legible de la entidad."""


class Cliente(Entidad):
    def __init__(self, identificador, nombre, correo, telefono):
        super().__init__(identificador)
        self.__nombre = texto(nombre, 'Nombre')
        correo = texto(correo, 'Correo')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', correo):
            raise DatosInvalidos('Correo electrónico inválido.')
        self.__correo = correo
        telefono = texto(telefono, 'Teléfono')
        if not re.fullmatch(r'\+?[0-9]{7,15}', telefono):
            raise DatosInvalidos('El teléfono debe contener entre 7 y 15 dígitos.')
        self.__telefono = telefono

    @property
    def nombre(self):
        return self.__nombre

    @property
    def correo(self):
        return self.__correo

    @property
    def telefono(self):
        return self.__telefono

    def describir(self):
        return f'{self.identificador}: {self.nombre} ({self.correo})'


class Servicio(Entidad, ABC):
    def __init__(self, identificador, nombre, tarifa):
        super().__init__(identificador)
        self.__nombre = texto(nombre, 'Nombre del servicio')
        self.__tarifa = numero(tarifa, 'Tarifa por hora', Decimal('0.01'))
        self.__disponible = True

    @property
    def nombre(self):
        return self.__nombre

    @property
    def tarifa(self):
        return self.__tarifa

    @property
    def disponible(self):
        return self.__disponible

    def cambiar_disponibilidad(self, disponible):
        if not isinstance(disponible, bool):
            raise DatosInvalidos('La disponibilidad debe ser True o False.')
        self.__disponible = disponible

    @abstractmethod
    def validar_parametros(self, duracion):
        pass

    @abstractmethod
    def costo_base(self, duracion):
        pass

    def calcular_costo(self, duracion, impuesto=0, descuento=0):
        """Variantes: costo(horas), costo(horas, impuesto), costo(..., descuento).

        Impuesto y descuento son proporciones entre 0 y 1.
        Se descuenta primero y luego se aplica el impuesto.
        """
        self.validar_parametros(duracion)
        impuesto = numero(impuesto, 'Impuesto', maximo=Decimal('1'))
        descuento = numero(descuento, 'Descuento', maximo=Decimal('1'))
        try:
            total = self.costo_base(duracion) * (1 - descuento) * (1 + impuesto)
            return total.quantize(Decimal('0.01'))
        except InvalidOperation as causa:
            raise DatosInvalidos('El cálculo excede la precisión monetaria.') from causa


class Sala(Servicio):
    def __init__(self, identificador, nombre, tarifa, capacidad):
        super().__init__(identificador, nombre, tarifa)
        capacidad = numero(capacidad, 'Capacidad', Decimal('1'))
        if capacidad != capacidad.to_integral_value():
            raise DatosInvalidos('La capacidad debe ser un entero.')
        self.__capacidad = int(capacidad)

    def validar_parametros(self, duracion):
        numero(duracion, 'Horas de sala', Decimal('1'), Decimal('12'))

    def costo_base(self, duracion):
        self.validar_parametros(duracion)
        return self.tarifa * numero(duracion, 'Duración')

    def describir(self):
        return f'{self.identificador}: Sala {self.nombre}, {self.__capacidad} personas, ${self.tarifa}/hora'


class Equipo(Servicio):
    def __init__(self, identificador, nombre, tarifa, seguro):
        super().__init__(identificador, nombre, tarifa)
        self.__seguro = numero(seguro, 'Seguro')

    def validar_parametros(self, duracion):
        numero(duracion, 'Horas de equipo', Decimal('1'), Decimal('72'))

    def costo_base(self, duracion):
        self.validar_parametros(duracion)
        return self.tarifa * numero(duracion, 'Duración') + self.__seguro

    def describir(self):
        return f'{self.identificador}: Equipo {self.nombre}, ${self.tarifa}/hora + seguro ${self.__seguro}'


class Asesoria(Servicio):
    def __init__(self, identificador, nombre, tarifa, especialidad):
        super().__init__(identificador, nombre, tarifa)
        self.__especialidad = texto(especialidad, 'Especialidad')

    def validar_parametros(self, duracion):
        numero(duracion, 'Horas de asesoría', Decimal('0.5'), Decimal('8'))

    def costo_base(self, duracion):
        self.validar_parametros(duracion)
        horas = numero(duracion, 'Duración')
        return self.tarifa * horas * (Decimal('0.90') if horas >= 4 else 1)

    def describir(self):
        return f'{self.identificador}: Asesoría {self.nombre}, {self.__especialidad}, ${self.tarifa}/hora'


class Estado(Enum):
    PENDIENTE = 'Pendiente'
    CONFIRMADA = 'Confirmada'
    PROCESADA = 'Procesada'
    CANCELADA = 'Cancelada'


class Reserva(Entidad):
    def __init__(self, identificador, cliente, servicio, duracion):
        super().__init__(identificador)
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise DatosInvalidos('Se requieren objetos Cliente y Servicio.')
        servicio.validar_parametros(duracion)
        if not servicio.disponible:
            raise OperacionNoPermitida('Servicio no disponible.')
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = numero(duracion, 'Duración')
        self.__estado = Estado.PENDIENTE
        self.__total = None

    @property
    def estado(self):
        return self.__estado

    @property
    def total(self):
        return self.__total

    def confirmar(self):
        if self.estado != Estado.PENDIENTE:
            raise OperacionNoPermitida('Solo se confirman reservas pendientes.')
        if not self.__servicio.disponible:
            raise OperacionNoPermitida('El servicio ya no está disponible.')
        self.__servicio.cambiar_disponibilidad(False)
        self.__estado = Estado.CONFIRMADA

    def cancelar(self):
        if self.estado not in (Estado.PENDIENTE, Estado.CONFIRMADA):
            raise OperacionNoPermitida('La reserva ya fue cancelada o procesada.')
        if self.estado == Estado.CONFIRMADA:
            self.__servicio.cambiar_disponibilidad(True)
        self.__estado = Estado.CANCELADA

    def procesar(self, impuesto=0, descuento=0):
        if self.estado != Estado.CONFIRMADA:
            raise OperacionNoPermitida('Debe confirmar la reserva antes de procesarla.')
        try:
            total = self.__servicio.calcular_costo(self.__duracion, impuesto, descuento)
        except DatosInvalidos as causa:
            raise OperacionNoPermitida('No se pudo procesar el costo de la reserva.') from causa
        else:
            self.__total = total
            self.__estado = Estado.PROCESADA
            self.__servicio.cambiar_disponibilidad(True)
            return total

    def describir(self):
        return (f'{self.identificador}: {self.__cliente.nombre} / {self.__servicio.nombre} / '
                f'{self.__duracion} horas / {self.estado.value} / total: {self.total}')


class Sistema:
    def __init__(self):
        self.__clientes = []
        self.__servicios = []
        self.__reservas = []

    @property
    def clientes(self):
        return tuple(self.__clientes)

    @property
    def servicios(self):
        return tuple(self.__servicios)

    @property
    def reservas(self):
        return tuple(self.__reservas)

    @staticmethod
    def buscar(coleccion, identificador):
        for entidad in coleccion:
            if entidad.identificador == identificador:
                return entidad
        raise NoEncontrado(f'No existe el identificador {identificador}.')

    def registrar_cliente(self, *args, **kwargs):
        cliente = Cliente(*args, **kwargs)
        self.__agregar(self.__clientes, cliente)
        return cliente

    def registrar_servicio(self, tipo, *args, **kwargs):
        tipos = {'sala': Sala, 'equipo': Equipo, 'asesoria': Asesoria}
        if tipo not in tipos:
            raise DatosInvalidos('Tipo de servicio desconocido.')
        servicio = tipos[tipo](*args, **kwargs)
        self.__agregar(self.__servicios, servicio)
        return servicio

    @staticmethod
    def __agregar(coleccion, entidad):
        if any(e.identificador == entidad.identificador for e in coleccion):
            raise DatosInvalidos(f'Identificador duplicado: {entidad.identificador}.')
        coleccion.append(entidad)

    def crear_reserva(self, identificador, cliente_id, servicio_id, duracion):
        reserva = Reserva(identificador, self.buscar(self.__clientes, cliente_id),
                          self.buscar(self.__servicios, servicio_id), duracion)
        self.__agregar(self.__reservas, reserva)
        return reserva


def configurar_log():
    ruta = Path(__file__).with_name('software_fj.log')
    logging.basicConfig(filename=ruta, encoding='utf-8', level=logging.INFO,
                        format='%(asctime)s | %(levelname)s | %(message)s', force=True)
    return ruta


def ejecutar(descripcion, accion):
    """Frontera de la aplicación: registra fallos y permite seguir operando."""
    try:
        resultado = accion()
    except (ErrorSistema, TypeError, ValueError, EOFError) as error:
        logging.exception('ERROR: %s', descripcion)
        print(f'[ERROR] {descripcion}: {error}')
    except Exception as error:
        logging.exception('ERROR INESPERADO: %s', descripcion)
        print(f'[ERROR INESPERADO] {descripcion}: {error}')
    else:
        logging.info('OK: %s', descripcion)
        detalle = resultado.describir() if isinstance(resultado, Entidad) else resultado
        print(f'[OK] {descripcion}' + (f': {detalle}' if detalle is not None else ''))
        return resultado
    finally:
        logging.info('Fin de operación: %s', descripcion)


def demostracion(sistema):
    pasos = [
        ('Registrar cliente válido', lambda: sistema.registrar_cliente('C1', 'Ana Pérez', 'ana@correo.com', '3001234567')),
        ('Rechazar correo inválido', lambda: sistema.registrar_cliente('C2', 'Luis', 'incorrecto', '3001234567')),
        ('Rechazar parámetro faltante', lambda: sistema.registrar_cliente('C3', 'Pedro')),
        ('Rechazar cliente duplicado', lambda: sistema.registrar_cliente('C1', 'Ana', 'ana@correo.com', '3001234567')),
        ('Crear sala', lambda: sistema.registrar_servicio('sala', 'S1', 'Sala A', 50000, 10)),
        ('Crear equipo', lambda: sistema.registrar_servicio('equipo', 'S2', 'Proyector', 20000, 5000)),
        ('Crear asesoría', lambda: sistema.registrar_servicio('asesoria', 'S3', 'Python', 80000, 'Programación')),
        ('Rechazar tarifa negativa', lambda: sistema.registrar_servicio('sala', 'S4', 'Sala B', -1, 5)),
        ('Rechazar capacidad fraccionaria', lambda: sistema.registrar_servicio('sala', 'S5', 'Sala C', 100, 2.5)),
        ('Rechazar cliente inexistente', lambda: sistema.crear_reserva('R0', 'C9', 'S1', 2)),
        ('Rechazar duración inválida', lambda: sistema.crear_reserva('R0', 'C1', 'S1', -2)),
        ('Crear reserva', lambda: sistema.crear_reserva('R1', 'C1', 'S1', 2)),
        ('Confirmar reserva', lambda: sistema.buscar(sistema.reservas, 'R1').confirmar()),
        ('Rechazar servicio ocupado', lambda: sistema.crear_reserva('R2', 'C1', 'S1', 1)),
        ('Rechazar descuento inválido', lambda: sistema.buscar(sistema.reservas, 'R1').procesar(descuento=2)),
        ('Procesar con impuesto y descuento', lambda: sistema.buscar(sistema.reservas, 'R1').procesar('0.19', '0.10')),
        ('Rechazar cancelar reserva procesada', lambda: sistema.buscar(sistema.reservas, 'R1').cancelar()),
        ('Crear reserva de equipo', lambda: sistema.crear_reserva('R3', 'C1', 'S2', 3)),
        ('Confirmar equipo', lambda: sistema.buscar(sistema.reservas, 'R3').confirmar()),
        ('Cancelar equipo', lambda: sistema.buscar(sistema.reservas, 'R3').cancelar()),
        ('Crear reserva de asesoría', lambda: sistema.crear_reserva('R4', 'C1', 'S3', 4)),
        ('Confirmar asesoría', lambda: sistema.buscar(sistema.reservas, 'R4').confirmar()),
        ('Procesar asesoría', lambda: sistema.buscar(sistema.reservas, 'R4').procesar()),
    ]
    for indice, (descripcion, accion) in enumerate(pasos, 1):
        ejecutar(f'{indice:02d}. {descripcion}', accion)
    print(f'\nDemostración terminada: {len(pasos)} operaciones. Los errores no detuvieron el programa.')


def menu(sistema):
    while True:
        print('\nSOFTWARE FJ\n1. Registrar cliente\n2. Registrar servicio\n3. Crear reserva'
              '\n4. Confirmar reserva\n5. Procesar reserva\n6. Cancelar reserva\n7. Listar datos\n0. Salir')
        try:
            opcion = input('Opción: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nSesión terminada.')
            break
        if opcion == '0':
            break

        def accion():
            if opcion == '1':
                return sistema.registrar_cliente(input('ID: '), input('Nombre: '), input('Correo: '), input('Teléfono: '))
            if opcion == '2':
                tipo = input('Tipo (sala/equipo/asesoria): ').strip().lower()
                if tipo not in ('sala', 'equipo', 'asesoria'):
                    raise DatosInvalidos('Tipo de servicio desconocido.')
                datos = [input('ID: '), input('Nombre: '), input('Tarifa por hora: ')]
                extra = input({'sala': 'Capacidad: ', 'equipo': 'Seguro fijo: ', 'asesoria': 'Especialidad: '}[tipo])
                return sistema.registrar_servicio(tipo, *datos, extra)
            if opcion == '3':
                return sistema.crear_reserva(input('ID reserva: '), input('ID cliente: '), input('ID servicio: '), input('Horas: '))
            if opcion in ('4', '5', '6'):
                reserva = sistema.buscar(sistema.reservas, input('ID reserva: ').strip())
                if opcion == '4':
                    return reserva.confirmar()
                if opcion == '6':
                    return reserva.cancelar()
                return reserva.procesar(input('Impuesto (0 a 1): '), input('Descuento (0 a 1): '))
            if opcion == '7':
                for titulo, entidades in [('Clientes', sistema.clientes), ('Servicios', sistema.servicios), ('Reservas', sistema.reservas)]:
                    print(f'\n{titulo}:')
                    for entidad in entidades:
                        print(entidad.describir())
                return
            raise DatosInvalidos('Opción no válida.')

        try:
            ejecutar(f'Menú {opcion}', accion)
        except KeyboardInterrupt:
            logging.info('Entrada cancelada por el usuario.')
            print('\nOperación interrumpida; regreso al menú.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='Ejecuta 23 operaciones de demostración.')
    args = parser.parse_args()
    try:
        ruta_log = configurar_log()
    except OSError as error:
        raise SystemExit(f'No se pudo abrir el archivo de logs: {error}')
    logging.info('Inicio de Software FJ: %s', datetime.now().isoformat())
    sistema = Sistema()
    if args.demo:
        demostracion(sistema)
    else:
        menu(sistema)
    logging.info('Cierre de Software FJ')
    print(f'Log de eventos y errores: {ruta_log}')
