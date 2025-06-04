# Bot Bancario Conversacional

## Objetivo
Diseñar una solución conversacional para un bot bancario en Telegram, integrando funcionalidades clave del sector financiero, inteligencia artificial y buenas prácticas de desarrollo.

## Puntos clave
Construir un bot conversacional para Telegram que simule la interacción con servicios típicos de una entidad bancaria.
Dicho bot debe comprender lenguaje natural y responder con información relevante y contextual

## Funcionalidades a implementar
1. Autenticación inicial
Se solicitara un PIN simulado al inicio de la conversación para acceder a las funcionalidades.
2. Consultar saldo y movimientos.
El bot debe interpretar mensajes del usuario como "¿Cuánto tengo en mi cuenta?" o "Mostrame los últimos movimientos" y responder con información simulada de cuentas y transacciones.
3. Simulación de préstamo.
Al recibir mensajes como "Necesito un préstamo" o “¿Cuánto pagaría si pido 100.000 en 24 cuotas?” el bot debe calcular una cuota estimada, mostrar tasa de interés, y un total a pagar. Adaptar condiciones según el perfil simulado del usuario.
4. Consultas generales.
El bot debera ser capaz de interpretar y responder preguntas relacionadas al negocio bancario como por ejemplo: “¿Qué tarjetas ofrecen?”, “¿Conviene un plazo fijo?”, “¿Cuál es la tasa para préstamos personales?”, etc.
5. Persistencia.
El bot guardara por usuario datos como: Informacion de cuenta, historial de movimientos, prestamos simulados, numero de interacciones.

## Partes pendientes y/o partes modificadas
* Debido a un problema de comprension lectora, se malinterpreto el punto 1.
El bot final no pide un PIN al inicio de la conversación, se puede mantener una 
conversación normal, pero al intentar acceder a información sensible 
como saldo de la cuenta, movimientos o prestamos el bot solicitara el PIN del usuario.

* Existe un comando que no fue utilizado en el video de prueba que es /setpin con el cual
el usuario puede cambiar su pin

* No se utilizaron clases debido a que es un codigo que no tendra mayor escala, pero se 
busco dejar el codigo separado por "if" y marcado con comentarios claros sobre la 
funcion de cada parte

## Observaciones
* Al iniciar el bot con el comando /start el mismo guarda automaticamente el nombre e id de telegram
del usuario en cuestion, no avisa al usuario y el mismo no puede borrar sus datos luego de iniciar.

* En la base de datos se encuentran hardcodeados algunos movimientos, prestamos e información de la
cuenta, sin embargo no tiene un "numero de interacciónes" implementado.

## Solucion obtenida
### Click en la imagen para ver un video utilizando el bot
[![Video prueba](https://img.freepik.com/vector-premium/concepto-chatbot-espacio-copia-texto-fondo-azul-vectorial-disenos-comunicacion-ia-asistencia-digital-proyectos-relacionados-tecnologia_1020043-804.jpg)](https://youtu.be/n_WYuVG-G4g)
