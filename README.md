# Software FJ — Fase 4

Proyecto de consola en Python 3.10 o superior, sin librerías externas ni base de datos.
Los datos viven en objetos y listas durante la ejecución. Al cerrar se pierden;
únicamente los eventos y errores se escriben en `software_fj.log`.

## Ejecutar

Abre una terminal dentro de esta carpeta:

```console
python main.py --demo
python main.py
python -m unittest -v
```

La primera orden ejecuta 23 operaciones válidas e inválidas. La segunda abre
el menú para registrar clientes, crear servicios y gestionar reservas.
Cada ejecución comienza con listas vacías. Si Windows tiene instalado Python
mediante el lanzador `py`, puedes sustituir `python` por `py`.

## Diseño y relación con el enunciado

| Requisito | Implementación |
| --- | --- |
| Entidad abstracta | `Entidad`, identificador de solo lectura y `describir()` abstracto. |
| Clientes encapsulados | `Cliente`, atributos privados y propiedades de lectura; valida nombre, correo y teléfono. |
| Servicio abstracto | `Servicio`, tarifa positiva, disponibilidad y cálculo común. |
| Herencia y polimorfismo | `Sala`, `Equipo` y `Asesoria` sobrescriben `describir`, `validar_parametros` y `costo_base`. |
| Reserva | Integra cliente y servicio, duración, estado y total; confirma, cancela y procesa. |
| Variantes del cálculo | `calcular_costo(horas, impuesto=0, descuento=0)` usa argumentos opcionales. Python no conserva varias definiciones de un método con el mismo nombre como Java. |
| Listas internas | `Sistema` conserva listas privadas; expone tuplas para impedir agregados externos. |
| Excepciones personalizadas | `DatosInvalidos`, `NoEncontrado`, `OperacionNoPermitida`. |
| Manejo avanzado | `ejecutar()` usa `try/except/else/finally`; `procesar()` encadena excepciones con `raise ... from causa`. |
| Registro de errores | El límite de ejecución del menú y de la demostración registra trazas completas con `logging.exception`. |
| Simulación | `demostracion()` realiza 23 operaciones y continúa después de los errores esperados. |

## Reglas adoptadas para completar el ejercicio

El PDF no fija tarifas, duraciones ni políticas comerciales. Este proyecto adopta:

- Sala: de 1 a 12 horas; costo = tarifa por hora × duración.
- Equipo: de 1 a 72 horas; costo = tarifa por hora × duración + seguro fijo.
- Asesoría: de 0.5 a 8 horas; descuento automático de 10 % desde 4 horas.
- Impuesto y descuento opcionales se escriben como proporciones: `0.19` es 19 %.
- Total = costo base × (1 − descuento) × (1 + impuesto), redondeado a dos decimales con `Decimal`.
- El descuento opcional se suma al beneficio de asesoría mediante aplicación sucesiva.
- Una reserva comienza pendiente. Confirmarla ocupa el servicio; procesarla representa
  completar el servicio y libera su disponibilidad. Cancelar una confirmada también lo libera.
- No se permite procesar pendientes, volver a confirmar, ni cancelar reservas procesadas.
- La disponibilidad representa un solo recurso por servicio; no hay agenda por fechas.
  Las reservas pendientes no bloquean recursos y su disponibilidad se revisa al confirmar.
- Los identificadores son únicos dentro de cada lista.

## Cómo explicar la ejecución

1. Ejecuta la demostración: muestra registros válidos, correo inválido, parámetros
   faltantes, duplicados, tarifas negativas y reservas fallidas.
2. La reserva de sala por dos horas vale 100000; con descuento de 10 % e impuesto
   de 19 % resulta en **107100.00**.
3. Un descuento inválido no cambia el estado ni el total. Después se procesa correctamente.
4. La asesoría de cuatro horas vale **288000.00**, por el descuento automático.
5. Abre `software_fj.log` para revisar eventos, trazas y causas encadenadas.
6. Ejecuta las pruebas para comprobar cálculos, validación, conflictos y estados.

Los errores de entrada y de negocio se controlan dentro de la aplicación. Si el sistema
operativo no permite abrir el archivo de logs, se informa el problema y se termina
al inicio; no se puede garantizar continuidad ante fallos del entorno o del equipo.
