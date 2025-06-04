import telebot
from telebot import types
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from db import baseDatos
import sqlite3
from datetime import datetime


load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN or not API_KEY:
    print("¡Error! Asegúrate de que TELEGRAM_BOT_TOKEN y GOOGLE_API_KEY están definidos en tu archivo .env")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
logger.info("Bot de Telegram inicializado.")

try:
    genai.configure(api_key=API_KEY)
    generation_config = {"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    logger.info("Modelo Gemini 'gemini-1.5-flash-latest' inicializado.")
except Exception as e:
    logger.error(f"Error al configurar o inicializar Gemini: {e}")
    exit()

def db_connect():
    return sqlite3.connect('datos_del_usuario.db')

user_action_pending_pin_verification = {}

# COMANDO INICIAL DEL BOT GUARDARA AL USUARIO EN LA DB
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Comando /start recibido de {message.from_user.username} (ID: {message.from_user.id})")
    telegram_id = message.from_user.id
    name = message.from_user.first_name
    insert_user(telegram_id, name)
    bot.reply_to(message, f'¡Hola {message.from_user.first_name}! Bienvenido a IceCash su banco de confianza\nDime en que puedo ayudarte hoy.')

@bot.message_handler(commands=['help'])
def send_help(message):
    logger.info(f"Comando /help recibido de {message.from_user.username}")
    help_text = """
        Aquí tienes los comandos que entiendo:
        /start - Inicia la conversación.
        /setpin - Agrega un pin de 4 digitos a tu cuenta.
        Si me escribes cualquier otra cosa, intentaré ayudarte usando IA.
        """
    bot.reply_to(message, help_text)

# FUNCION PARA INGRESAR AL USUARIO DENTRO DE LA DB
def insert_user(telegram_id: int, name: str):
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, name)
            VALUES (?, ?)
        ''', (telegram_id, name))
        conn.commit()
        logger.info(f"Usuario {name} (ID: {telegram_id}) insertado o ya existente.")
    except sqlite3.Error as e:
        logger.error(f"Error al insertar usuario {telegram_id}: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# FUNCION PARA OBTENER DE LA DB LOS DATOS DE LA CUENTA DEL USUARIO
def get_user_accounts_info(telegram_id: int) -> str:
    conn = db_connect()
    cursor = conn.cursor()
    info_parts = []
    try:
        cursor.execute('''
            SELECT name, dinero, currency FROM cuentas WHERE telegram_id = ? 
        ''', (telegram_id,))
        cuentas = cursor.fetchall()
        if cuentas:
            info_parts.append("Estado de tus cuentas:")
            for cuenta_data in cuentas: 
                info_parts.append(f"- {cuenta_data[0]}: ${cuenta_data[1]:.2f} {cuenta_data[2] or ''}")
        else:
            info_parts.append("No tienes cuentas registradas actualmente.")
        cursor.execute('''
            SELECT c.name as account_name, h.name as mov_description, h.dinero as mov_amount, h.timestamp 
            FROM hmovimientos h
            JOIN cuentas c ON h.account_id = c.id
            WHERE h.telegram_id = ? ORDER BY h.timestamp DESC LIMIT 5 
        ''', (telegram_id,))
        movimientos = cursor.fetchall()
        if movimientos:
            info_parts.append("\nTus últimos movimientos:")
            for mov in movimientos:
                timestamp_str = f" ({datetime.strptime(mov[3], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')})" if mov[3]else ""
                info_parts.append(f"- [{mov[0]}] {mov[1]}: ${mov[2]:.2f}{timestamp_str}")
        else:
            info_parts.append("\nNo tienes movimientos recientes.")
    except sqlite3.Error as e:
        logger.error(f"Error al obtener datos de cuentas/movimientos para {telegram_id}: {e}")
        return "Hubo un error al consultar tu información de cuentas."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return "\n".join(info_parts) if info_parts else "No se encontró información de cuentas o movimientos."

# FUNCION PARA OBTENER DE LA DB LOS DATOS DE LOS PRESTAMOS DEL USUARIO
def get_user_loans_info(telegram_id: int) -> str:
    conn = db_connect()
    cursor = conn.cursor()
    info_parts = []
    try:
        cursor.execute('''
            SELECT name, dinero, dineroEntregado, due_date FROM prestamos WHERE telegram_id = ?
        ''', (telegram_id,)) 
        prestamos = cursor.fetchall()
        if prestamos:
            info_parts.append("Tus préstamos activos:")
            for p in prestamos:
                nombre_prestamo = p[0]
                monto_total = p[1]
                monto_pagado = p[2] if p[2] is not None else 0 
                pendiente = monto_total - monto_pagado
                due_date_str = f". Vence: {datetime.strptime(p[3], '%Y-%m-%d').strftime('%d/%m/%Y')}" if p[3] else ""
                info_parts.append(f"- {nombre_prestamo}: Total ${monto_total:.2f}, Pagado ${monto_pagado:.2f}, Pendiente ${pendiente:.2f}{due_date_str}")
        else:
            info_parts.append("No tienes préstamos activos actualmente.")
    except sqlite3.Error as e:
        logger.error(f"Error al obtener datos de préstamos para {telegram_id}: {e}")
        return "Hubo un error al consultar tu información de préstamos."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    return "\n".join(info_parts) if info_parts else "No se encontró información de préstamos."

# FUNCION PARA COMPROBAR QUE EL PIN QUE ENVIO EL USUARIO ES EL PIN DE SU CUENTA EN LA DB
def check_pin(telegram_id: int, entered_pin: str) -> bool:
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT pin FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        if result and result[0] is not None: 
            stored_pin = result[0]
            return stored_pin == entered_pin
        elif result and result[0] is None: 
            logger.warning(f"Usuario {telegram_id} intentó verificar PIN pero no tiene uno configurado.")
            return False 
        else: 
            logger.error(f"Usuario {telegram_id} no encontrado al verificar PIN.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error de BD al verificar PIN para {telegram_id}: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# FUNCION PARA ASIGNAR UN NUEVO PIN O MODIFICAR EL PIN DEL USUARIO
@bot.message_handler(commands=['setpin'])
def set_pin_command(message):
    telegram_id = message.from_user.id
    conn = None 
    cursor = None
    try:
        new_pin_parts = message.text.split(maxsplit=1)
        if len(new_pin_parts) < 2:
            bot.reply_to(message, "Por favor, proporciona un PIN. Ejemplo: `/setpin 1234`")
            return
        new_pin = new_pin_parts[1].strip()
        if not new_pin.isdigit() or len(new_pin) != 4:
            bot.reply_to(message, "El PIN debe ser numérico y de 4 dígitos. Ejemplo: `/setpin 1234`")
            return
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET pin = ? WHERE telegram_id = ?", (new_pin, telegram_id))
        conn.commit()
        if cursor.rowcount > 0:
            bot.reply_to(message, f"¡Tu PIN ha sido configurado/actualizado a {new_pin}!")
            logger.info(f"PIN actualizado para usuario {telegram_id}")
        else:
            bot.reply_to(message, "No pude actualizar tu PIN. Asegúrate de haber iniciado el bot con /start primero.")
    except sqlite3.Error as e: 
        logger.error(f"Error de BD al configurar PIN para {telegram_id}: {e}")
        bot.reply_to(message, "Ocurrió un error al intentar configurar tu PIN.")
    except Exception as e: 
        logger.error(f"Error inesperado al configurar PIN: {e}")
        bot.reply_to(message, "Ocurrió un error inesperado.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# PALABRAS CLAVE QUE SE BUSCARAN EN EL MENSAJE DEL USUARIO PARA DETERMINAR SI QUIERE ACCEDER A SUS DATOS O QUIERE CONSULTAR COSAS EN GENERAL
keywords_saldo = ["saldo", "cuánto tengo", "en mi cuenta", "últimos movimientos", "movimientos", "estado de cuenta", "balance",  "ver mi saldo", "consultar saldo", "mostrar saldo", "qué saldo tengo",
    "ver movimientos", "consultar movimientos", "mostrar movimientos", "historial de cuenta","detalle de mi cuenta", "actividad de cuenta", "transacciones recientes","dinero en cuenta", "plata en cuenta", ]
keywords_prestamo = ["préstamo", "prestamos", "mis prestamos", "ver prestamos", "estado de mi préstamo", "cuánto debo", "deuda préstamo", "préstamos activos"]
keywords_generales = ["tarjetas ofrecen", "conviene un plazo fijo", "cuál es la tasa para préstamos personales", "información general", "productos bancarios", "general", "tipos de tarjeta", "tarjeta de débito", "tarjeta de crédito", "beneficios tarjeta",
    "costo tarjeta", "comisiones tarjeta", "tarjeta internacional", "tarjeta nacional", "tasas de interés", "tasas plazo fijo", ]

# FUNCION PARA HACER QUE EL MENSAJE DEL USUARIO SEA MINUSCULA, LUEGO COMPRUEBA SI LAS PALABRAS CLAVE ESTAN EN EL MENSAJE O NO 
def check_keywords(text: str, keywords: list) -> bool:
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

# NUCLEO CENTRAL DEL BOT, GENERA LAS RESPUESTAS EN FUNCION DE LOS FILTROS (SI QUIERE SUS DATOS DE LA DB SALDO/PRESTAMO, SI QUIERE INFO GENERAL U OTROS)
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_non_command_message(message):
    # COMPROBAMOS QUE EL MENSAJE TENGA TEXTO PARA INTERPRETAR
    if message.text is None:
        logger.warning(f"Mensaje recibido sin texto (tipo: {message.content_type}). Ignorando.")
        return 
    user_input = message.text.strip()
    telegram_id = message.from_user.id
    username_display = message.from_user.first_name
    user_info = f"{username_display}"
    logger.info(f"--- INICIO handle_non_command_message para input: '{user_input}' ---") 

    ###################
    ## PRIMER BLOQUE ##
    ###################

    # VERIFICAMOS SI EL MENSAJE DEL USUARIO ES NUMERO, DE SER NUMERO Y TENER 4 DIGITOS ASUMIMOS QUE ES UN PIN
    # COMPROBAMOS SI EL USUARIO TIENE ALGUNA FUNCION ESPERANDO UN PIN PARA EJECUTARSE
    if user_input.isdigit() and len(user_input) == 4 and telegram_id in user_action_pending_pin_verification:
        logger.info(f"Usuario {user_info} envió un posible PIN: '{user_input}'")
        entered_pin = user_input
        function_to_call = user_action_pending_pin_verification.pop(telegram_id) 
        conn_pin_check = None
        cursor_pin_check = None
        logger.info("--- DENTRO DE handle_non_command_message ---")

        # INTENTAMOS EXTRAER EL PIN DEL USUARIO DE LA DB
        try:
            conn_pin_check = db_connect()
            cursor_pin_check = conn_pin_check.cursor()
            cursor_pin_check.execute("SELECT pin FROM users WHERE telegram_id = ?", (telegram_id,))
            user_db_data = cursor_pin_check.fetchone() 
            logger.info(f"DEBUG PIN BLOCK: user_db_data para {telegram_id} es: {user_db_data}") 
            # SI EL USUARIO NO EXISTE O NO TIENE PIN, CORTAMOS EL FLUJO AQUI Y PEDIMOS QUE CONFIGURE UNO
            if not user_db_data or not user_db_data[0]:
                bot.reply_to(message, "Parece que no uso el comando /start para iniciar o no tienes un PIN configurado. Por favor, usa el comando `/setpin TU_PIN_DE_4_DIGITOS` para crear uno.")
                return
            # SI EL USUARIO TIENE PIN LLAMAREMOS LA FUNCION CHECK_PIN PARA VERIFICARLO
            elif check_pin(telegram_id, entered_pin): 
                bot.send_message(message.chat.id, "PIN correcto. Accediendo a tu información...")
                db_data_message = function_to_call(telegram_id)
                if db_data_message:
                    bot.send_message(message.chat.id, db_data_message)
                else:
                    bot.send_message(message.chat.id, "No pude recuperar la información solicitada en este momento.")
            else:
                bot.send_message(message.chat.id, "PIN incorrecto. Por seguridad, no se mostrará la información.")
        except Exception as e_handler_init:
            logger.error(f"Error procesando el PIN ingresado para {user_info}: {e_pin_processing}", exc_info=True)
            bot.reply_to(message, "Ocurrió un error al verificar tu PIN. Intenta de nuevo.")
        finally:
            if cursor_pin_block: cursor_pin_block.close() 
            if conn_pin_block: conn_pin_block.close()
        logger.info(f"--- FIN (procesado como PIN) handle_non_command_message para input: '{user_input}' de {user_info} ---")
        return 
    logger.info(f"Mensaje no-comando (consulta regular) recibido de {user_info}: '{user_input}'")
    
    ####################
    ## SEGUNDO BLOQUE ##
    ####################

    # SI EL FLUJO LLEGO AQUI ES PORQUE EL MENSAJE NO ES UN PIN, ES UN MENSAJE DE TEXTO INTERPRETABLE
    # SETEAMOS LA VARIABLE DE FUNCION A EJECUTAR LUEGO DEL PIN COMO NONE YA QUE EL MENSAJE ES NORMAL, Y PIN REQUERIDO EN FALSO
    logger.info(f"Input NO es un PIN directo. Procesando como consulta regular: '{user_input}'") 
    function_to_execute_after_pin = None
    is_pin_required_action = False

    # YA QUE EL MENSAJE NO ES UN PIN COMPROBAREMOS SI EL MENSAJE ESTA EN EL CONTEXTO DE SALDOS/MOVIMIENTOS O PRESTAMOS
    # SI EL MENSAJE DEL USUARIO HACE REFERENCIA A ALGUNO DE LOS CONTEXTOS ANTERIORMENTE NOMB, 
    # ACTIVAREMOS LA FUNCION A EJ LUEGO Y EL PIN REQUERIDO EN TRUE EN SU CORRESPONDIENTE (SALDO/MOV O PRESTAMO)
    if check_keywords(user_input, keywords_saldo):
        logger.info(f"Palabra clave de SALDO detectada para '{user_input}' de {user_info}.")
        function_to_execute_after_pin = get_user_accounts_info
        is_pin_required_action = True
    elif check_keywords(user_input, keywords_prestamo):
        logger.info(f"Palabra clave de PRÉSTAMO detectada para '{user_input}' de {user_info}.")
        function_to_execute_after_pin = get_user_loans_info
        is_pin_required_action = True

    ###################
    ## TERCER BLOQUE ##
    ###################

    # AHORA VERIFICAREMOS SI EN EL IF ANTERIOR SE ACTIVO EL PIN REQUERIDO O NO
    # SI NO SE ACTIVO SALTAREMOS ESTE IF ENTERO
    if is_pin_required_action:
        logger.info(f"Acción '{function_to_execute_after_pin.__name__ if function_to_execute_after_pin else 'N/A'}' requiere PIN para {user_info}.")
        conn_check_has_pin = None
        cursor_check_has_pin = None
        try:
            # CONECTAMOS CON LA DB, EXTRAEMOS EL PIN DE LA DB, LO GUARDAMOS PARA VERIFICAR LUEGO
            conn_check = db_connect()
            cursor_check = conn_check.cursor()
            cursor_check.execute("SELECT pin FROM users WHERE telegram_id = ?", (telegram_id,))
            user_has_pin_data = cursor_check.fetchone()
            # VERIFICAMOS SI EL USUARIO EXISTE Y SI TIENE UN PIN
            # EL BOT SOLICITARA EL PIN Y LO LOGEARA SI EXISTE UNA FUNCION A EJECUTARSE LUEGO DEL PIN
            if user_has_pin_data and user_has_pin_data[0]: 
                bot.send_message(message.chat.id, "Por seguridad, por favor, envía tu PIN de 4 dígitos para continuar.")
                user_action_pending_pin_verification[telegram_id] = function_to_execute_after_pin
                if function_to_execute_after_pin: 
                    logger.info(f"Usuario {user_info} puesto en espera de PIN para {function_to_execute_after_pin.__name__}.")
            else: 
                    bot.send_message(message.chat.id, "Para esta acción necesitas un PIN. Por favor, configúralo con `/setpin TU_PIN_DE_4_DIGITOS` e intenta de nuevo.")
        except Exception as e_prepare_pin:
                logger.error(f"Error preparando para pedir PIN para {user_info}: {e_prepare_pin}", exc_info=True)
                bot.reply_to(message, "Hubo un problema al preparar la consulta. Intenta de nuevo.")
        finally:
            if cursor_check_has_pin: cursor_check_has_pin.close()
            if conn_check_has_pin: conn_check_has_pin.close()
            logger.info(f"--- FIN (acción requiere PIN, se solicitó o se indicó configurar) handle_non_command_message para input: '{user_input}' de {user_info} ---")
            return

    ###################
    ## CUARTO BLOQUE ##
    ###################

    # SI NO FUE REQUERIDO EL PIN EL FLUJO NOS TRAERA AQUI, SE CREAN LOS PROMPT PARA CONSULTAS GENERALES O INTERACCION CON EL BOT
    logger.info(f"Acción para '{user_input}' de {user_info} NO requiere PIN. Procediendo con Gemini.")
    prompt_content = "" 
    
    # CONSULTA SOBRE COSAS FINANCIERAS EN GENERAL O INTERACION CON EL BOT
    if check_keywords(user_input, keywords_generales):
        logger.info(f"Palabra clave GENERAL detectada para '{user_input}' de {user_info}.")
        prompt_content = f"""
        Eres un asistente amigable de IceCash.
        Un usuario ({user_info}) te ha enviado el siguiente mensaje: "{user_input}"
        Tu tarea es responder a su consulta general sobre productos o servicios bancarios.
        Tarjetas: "Valo Card" (débito nacional), "Mine Card" (crédito nacional), "Vault Card" (crédito internacional).
        Tasa préstamo promedio Uruguay: ~35% TEA (varía).
        Plazos fijos: en Pesos y Dólares, tasas competitivas.
        Responde directamente al usuario con naturalidad.
        """
    else:
        logger.info(f"Input '{user_input}' de {user_info} no coincide con categorías específicas. Usando prompt de FALLBACK.")
        prompt_content = f"""
        Eres un asistente amigable de IceCash.
        Un usuario ({user_info}) te ha enviado el siguiente mensaje: "{user_input}"
        Tu tarea es responder a la consulta del usuario de forma útil y CONCISA.
        Si no entiendes la pregunta o parece no estar relacionada con temas bancarios, puedes decirle que no estás seguro de cómo ayudar con eso y recordarle los temas principales sobre los que puede consultar: información sobre nuestros productos (tarjetas, plazos fijos, tasas de interés) o cómo usar los comandos del bot. También puede pedir ayuda con /help.
        Si la pregunta es muy general o no encaja en categorías específicas, intenta ser útil o pide que reformule.
        Anímale a preguntar. Responde directamente al usuario con naturalidad.
        """
    # ENVIAMOS EL PROMPT A LA INTELIGENCIA ARTIFICIAL PARA QUE GENERE SU RESPUESTA EN CONSECUENCIA
    if prompt_content:
        logger.info(f"Enviando a Gemini para {user_info} con prompt (primeros 200 chars): {prompt_content[:200]}...")
        try:
            response = model.generate_content(prompt_content)
            ai_full_response = ""
            if response.candidates and response.candidates[0].finish_reason.name == "STOP":
                if response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            ai_full_response += part.text
            else:
                reason = "UNKNOWN"
                safety_details_str = "No safety details available."
                if response.candidates and response.candidates[0].finish_reason:
                    reason = response.candidates[0].finish_reason.name
                    if reason == "SAFETY" and response.candidates[0].safety_ratings:
                        blocked_ratings = [
                            f"{sr.category.name.replace('HARM_CATEGORY_', '')}: {sr.probability.name}"
                            for sr in response.candidates[0].safety_ratings if sr.blocked
                        ]
                        safety_details_str = "Bloqueado por: " + ", ".join(blocked_ratings) if blocked_ratings else "Bloqueado por seguridad."
                logger.warning(f"Gemini no generó contenido válido para {user_info}. Razón: {reason}. Detalles: {safety_details_str}")
                bot.reply_to(message, f"Mi intento de respuesta fue bloqueado ({safety_details_str}). Por favor, intenta reformular tu pregunta.")
            if ai_full_response:
                logger.info(f"Respuesta de Gemini (consulta general) generada para {user_info}.")
                bot.reply_to(message, ai_full_response)
            elif not (response.candidates and response.candidates[0].finish_reason.name != "STOP"):
                logger.warning(f"Gemini generó una respuesta vacía para {user_info}. Prompt: {prompt_content[:200]}")
                bot.reply_to(message, "No pude generar una respuesta para eso en este momento, ¿podrías intentarlo de nuevo o reformular tu pregunta?")
        except Exception as e_gemini:
            logger.error(f"Error CRÍTICO al interactuar con Gemini API para {user_info}: {e_gemini}", exc_info=True)
            bot.reply_to(message, "Lo siento, ocurrió un error inesperado grave al procesar tu mensaje con la IA.\nIntenta de nuevo más tarde.")
    else:
        logger.warning(f"CRÍTICO: prompt_content está vacío. No se llamó a Gemini. Input: {user_input}") 
        logger.warning(f"No se identificó acción de PIN ni se generó prompt para Gemini. Input: {user_input}")
        bot.reply_to(message, "No estoy seguro de cómo ayudarte con eso. Puedes intentar preguntarme sobre productos generales o usar /help.")
    logger.info(f"--- FIN handle_non_command_message para input: '{user_input}' ---") 

# COMANDO PARA INICIAR EL BOT AL EJECUTAR EL CODIGO
if __name__ == "__main__":
    main_logger = logging.getLogger(__name__)
    main_logger.info("Iniciando script principal del bot...")

    main_logger.info("Ejecutando configuración de base de datos...")
    baseDatos.setup_database_and_insert_examples() 
    main_logger.info("Configuración de base de datos completada.")

    main_logger.info("Iniciando el bot de Telegram...")
    bot.infinity_polling(logger_level=logging.INFO) 
    main_logger.info("El bot de Telegram se ha detenido.")