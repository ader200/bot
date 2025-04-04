import os
import json
import qrcode
import uuid
from telebot import TeleBot, types
from datetime import datetime, timedelta
import random
import platform
import subprocess
import threading
import time
import certifi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Token del bot y configuraciones
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))

# Constantes
CHAT_OPERADOR = int(os.getenv('CHAT_OPERADOR'))
CHAT_SOPORTE = int(os.getenv('CHAT_SOPORTE'))
CHAT_HISTORIAL = int(os.getenv('CHAT_HISTORIAL'))
TIEMPO_INACTIVIDAD = int(os.getenv('TIEMPO_INACTIVIDAD'))

# Conexión a MongoDB
uri = os.getenv('MONGODB_URI')
client = MongoClient(
    uri,
    server_api=ServerApi('1'),
    tls=True,
    tlsAllowInvalidCertificates=True,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=30000,
    retryWrites=True,
    retryReads=True,
    tlsCAFile=certifi.where()
)
db = client[os.getenv('MONGODB_DB_NAME')]

# Colecciones de MongoDB
registro_collection = db.registro
compras_collection = db.compras
ganadores_collection = db.ganadores
gratis_collection = db.gratis
codigos_collection = db.codigos
links_collection = db.links
historial_rifa_collection = db.historial_rifa
historial_gratis_collection = db.historial_gratis
comprobantes_pendientes_collection = db.comprobantes_pendientes

# Inicializar el bot
bot = TeleBot(TOKEN)

# Variables globales
conversaciones_activas = {}
temporizadores = {}
conversaciones_soporte = {}
MAX_RETRIES = int(os.getenv('MAX_RETRIES'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY'))

# Constantes para directorios
CONVERSACIONES_DIR = 'conversaciones'

# Funciones de MongoDB
def inicializar_mongodb():
    """Inicializa las colecciones de MongoDB con sus estructuras base"""
    # Inicializar registro
    if registro_collection.count_documents({}) == 0:
        registro_collection.insert_one({'usuarios': []})
    
    # Inicializar compras
    if compras_collection.count_documents({}) == 0:
        compras_collection.insert_one({'compras': []})
    
    # Inicializar ganadores
    if ganadores_collection.count_documents({}) == 0:
        ganadores_collection.insert_one({'ganadores': []})
    
    # Inicializar gratis
    if gratis_collection.count_documents({}) == 0:
        gratis_collection.insert_one({'participantes': []})
    
    # Inicializar códigos
    if codigos_collection.count_documents({}) == 0:
        codigos_collection.insert_one({
            'codigos_disponibles': [],
            'codigos_usados': [],
            'codigos_activos': {},
            'estadisticas': {
                'total_codigos_generados': 0,
                'codigos_disponibles': 0,
                'codigos_usados': 0,
                'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    # Inicializar links
    if links_collection.count_documents({}) == 0:
        links_collection.insert_one({'links': []})
    
    # Inicializar historiales
    if historial_rifa_collection.count_documents({}) == 0:
        historial_rifa_collection.insert_one({'historial': {}})
    if historial_gratis_collection.count_documents({}) == 0:
        historial_gratis_collection.insert_one({'historial': {}})
    
    # Inicializar comprobantes pendientes
    if comprobantes_pendientes_collection.count_documents({}) == 0:
        comprobantes_pendientes_collection.insert_one({'comprobantes': []})

def cargar_datos(coleccion, campo=None):
    """Carga datos de una colección de MongoDB"""
    try:
        if campo:
            documento = coleccion.find_one({})
            if documento is None:
                # Si no hay documento, devolver un valor por defecto según el campo
                if campo in ['compras', 'participantes', 'links']:
                    return []
                elif campo == 'historial':
                    return {}
                else:
                    return {}
            
            valor = documento.get(campo)
            # Asegurarse de que el valor sea del tipo correcto
            if campo in ['compras', 'participantes', 'links'] and not isinstance(valor, list):
                return []
            elif campo == 'historial' and not isinstance(valor, dict):
                return {}
            return valor
        else:
            documento = coleccion.find_one({})
            if documento is None:
                return {}
            return documento
    except Exception as e:
        print(f"Error al cargar datos de {coleccion.name}: {e}")
        if campo in ['compras', 'participantes', 'links']:
            return []
        elif campo == 'historial':
            return {}
        else:
            return {}

def guardar_datos(coleccion, datos, campo=None):
    """Guarda datos en una colección de MongoDB"""
    try:
        # Primero eliminar todos los documentos existentes
        coleccion.delete_many({})
        
        # Luego insertar los nuevos datos
        if campo:
            coleccion.insert_one({campo: datos})
        else:
            coleccion.insert_one(datos)
        return True
    except Exception as e:
        print(f"Error al guardar datos en {coleccion.name}: {e}")
        return False

def mover_datos_a_historial():
    """Mueve los datos actuales a las colecciones de historial"""
    # Mover datos de rifas pagadas
    compras = cargar_datos(compras_collection, 'compras')
    historial_rifas = cargar_datos(historial_rifa_collection, 'historial')
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    
    # Asegurarse de que historial_rifas sea un diccionario
    if not isinstance(historial_rifas, dict):
        historial_rifas = {}
    
    if compras:
        historial_rifas[fecha_actual] = compras
        guardar_datos(historial_rifa_collection, historial_rifas, 'historial')
        guardar_datos(compras_collection, [], 'compras')
    
    # Mover datos de rifas gratis
    gratis = cargar_datos(gratis_collection, 'participantes')
    historial_gratis = cargar_datos(historial_gratis_collection, 'historial')
    
    # Asegurarse de que historial_gratis sea un diccionario
    if not isinstance(historial_gratis, dict):
        historial_gratis = {}
    
    if gratis:
        historial_gratis[fecha_actual] = gratis
        guardar_datos(historial_gratis_collection, historial_gratis, 'historial')
        guardar_datos(gratis_collection, [], 'participantes')

# Generar número único
def generar_numero_unico():
    return str(uuid.uuid4())

# Generar QR
def generar_qr(data, filename):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

def verificar_viernes():
    """Verifica si es viernes a las 10 PM"""
    now = datetime.now()
    return now.weekday() == 4 and now.hour == 22

def notificar_ganador(ganador, tipo_rifa):
    """Notifica al ganador y a los demás participantes"""
    if tipo_rifa == 'pagada':
        participantes = cargar_datos(compras_collection, 'compras')
        mensaje_ganador = (
            f"🎉 ¡Felicitaciones {ganador['nombre']}! 🎉\n\n"
            f"Has sido seleccionado como el ganador de la rifa de esta semana.\n"
            f"Compraste {ganador['cantidad']} boleto(s).\n\n"
            "Nos pondremos en contacto contigo pronto para coordinar la entrega de tu premio. 🏆"
        )
    else:
        participantes = cargar_datos(gratis_collection, 'participantes')
        mensaje_ganador = (
            f"🎉 ¡Felicitaciones {ganador['nombre']}! 🎉\n\n"
            f"Has sido seleccionado como el ganador de la rifa gratuita de esta semana.\n\n"
            "Nos pondremos en contacto contigo pronto para coordinar la entrega de tu premio. 🏆"
        )

    # Notificar al ganador
    bot.send_message(ganador['chat_id'], mensaje_ganador)

    # Notificar a los demás participantes
    mensaje_otros = (
        f"🎯 ¡Tenemos un ganador!\n\n"
        f"Felicitaciones a {ganador['nombre']}, quien ganó con {ganador.get('cantidad', 1)} boleto(s).\n\n"
        "No te desanimes, ¡la próxima semana podrías ser tú!\n"
        "Tenemos grandes sorpresas preparadas para los próximos sorteos. 🎁\n\n"
        "Usa /rifa o /gratis para participar en el próximo sorteo. 🍀"
    )

    for participante in participantes:
        if participante['chat_id'] != ganador['chat_id']:
            try:
                bot.send_message(participante['chat_id'], mensaje_otros)
            except:
                continue

# Funciones para el comando /cliente
def iniciar_chat_soporte(message):
    """Inicia un chat de soporte entre el cliente y el equipo de soporte"""
    chat_id = message.chat.id
    
    # Verificar si el cliente ya está en una conversación
    if chat_id in conversaciones_soporte:
        bot.reply_to(message, "❌ Ya tienes una conversación activa con soporte.")
        return
    
    # Crear la conversación
    conversaciones_soporte[chat_id] = {
        'inicio': datetime.now(),
        'mensajes': [],
        'atendido': False,
        'nombre_cliente': message.from_user.first_name
    }
    
    # Notificar al chat de soporte
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "✅ Atender",
        callback_data=f"atender_soporte_{chat_id}"
    ))
    
    bot.send_message(
        CHAT_SOPORTE,
        f"🆕 Nueva solicitud de soporte\n\n"
        f"👤 Cliente: {message.from_user.first_name}\n"
        f"🆔 ID: {chat_id}\n\n"
        "Presiona el botón para atender",
        reply_markup=markup
    )
    
    # Notificar al cliente
    bot.reply_to(message,
        "✅ Tu solicitud ha sido enviada al equipo de soporte.\n"
        "Por favor, espera a que un agente te atienda.\n\n"
        "Puedes usar /cerrar en cualquier momento para terminar la conversación.")

def procesar_mensaje_soporte(message):
    """Procesa los mensajes entre cliente y soporte"""
    chat_id = message.chat.id
    
    # Si el mensaje es del chat de soporte
    if message.chat.id == CHAT_SOPORTE:
        # Buscar el cliente en conversación activa
        for cliente_id, conv in conversaciones_soporte.items():
            if conv.get('atendido'):
                try:
                    # Asegurarse de que 'mensajes' sea una lista
                    if 'mensajes' not in conv:
                        conv['mensajes'] = []
                    elif not isinstance(conv['mensajes'], list):
                        conv['mensajes'] = []
                        
                    # Guardar mensaje
                    if message.text:
                        conv['mensajes'].append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'from_id': CHAT_SOPORTE,
                            'content': message.text,
                            'type': 'text'
                        })
                        # Enviar al cliente
                        bot.send_message(cliente_id, f"👨‍💼 Soporte: {message.text}")
                    elif message.photo:
                        conv['mensajes'].append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'from_id': CHAT_SOPORTE,
                            'content': '[imagen]',
                            'type': 'image',
                            'file_id': message.photo[-1].file_id
                        })
                        # Enviar al cliente
                        bot.send_photo(cliente_id, message.photo[-1].file_id, caption="👨‍💼 Imagen del soporte")
                except Exception as e:
                    print(f"Error al enviar mensaje al cliente: {e}")
                break
    
    # Si el mensaje es del cliente
    elif chat_id in conversaciones_soporte:
        conv = conversaciones_soporte[chat_id]
        
        # Solo procesar si la conversación está atendida
        if conv.get('atendido'):
            try:
                # Asegurarse de que 'mensajes' sea una lista
                if 'mensajes' not in conv:
                    conv['mensajes'] = []
                elif not isinstance(conv['mensajes'], list):
                    conv['mensajes'] = []
                    
                # Guardar mensaje
                if message.text:
                    conv['mensajes'].append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'from_id': chat_id,
                        'nombre': message.from_user.first_name,
                        'content': message.text,
                        'type': 'text'
                    })
                    # Enviar al chat de soporte
                    bot.send_message(CHAT_SOPORTE, f"👤 Cliente {message.from_user.first_name} (ID: {chat_id}):\n{message.text}")
                elif message.photo:
                    conv['mensajes'].append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'from_id': chat_id,
                        'nombre': message.from_user.first_name,
                        'content': '[imagen]',
                        'type': 'image',
                        'file_id': message.photo[-1].file_id
                    })
                    # Enviar al chat de soporte
                    bot.send_photo(CHAT_SOPORTE, message.photo[-1].file_id, caption=f"📸 Imagen de {message.from_user.first_name} (ID: {chat_id})")
            except Exception as e:
                print(f"Error al enviar mensaje al soporte: {e}")

def cerrar_chat_soporte(chat_id, tipo):
    """Cierra una conversación de soporte y guarda el historial"""
    if chat_id not in conversaciones_soporte:
        return
    
    conv = conversaciones_soporte[chat_id]
    
    # Obtener el historial de la conversación
    historial = conv['mensajes']
    if historial:
        # Crear mensaje principal con la información del cliente
        cliente_info = f"📝 Historial de conversación de soporte\n\n"
        cliente_info += f"🆔 ID del Chat: {chat_id}\n"
        cliente_info += f"👤 Cliente: {conv['nombre_cliente']}\n"
        cliente_info += f"⏰ Inicio: {conv['inicio'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        cliente_info += f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        cliente_info += f"👨‍💼 Atendido: {'Sí' if conv.get('atendido') else 'No'}\n\n"
        cliente_info += "💬 Mensajes:\n\n"
        
        # Separar mensajes de texto e imágenes
        mensajes_texto = []
        imagenes = []
        
        for msg in historial:
            if msg['type'] == 'text':
                nombre = msg.get('nombre', 'Usuario')
                timestamp = msg.get('timestamp', '')
                mensajes_texto.append(f"👤 {nombre} ({timestamp}): {msg['content']}")
            elif msg['type'] == 'image' and 'file_id' in msg:
                imagenes.append(msg)
        
        try:
            # Enviar mensaje principal con la información
            bot.send_message(CHAT_HISTORIAL, cliente_info)
            
            # Enviar todos los mensajes de texto en un solo mensaje
            if mensajes_texto:
                bot.send_message(CHAT_HISTORIAL, "\n".join(mensajes_texto))
            
            # Enviar imágenes por separado
            if imagenes:
                bot.send_message(CHAT_HISTORIAL, "\n📸 Imágenes de la conversación:")
                for msg in imagenes:
                    nombre = msg.get('nombre', 'Usuario')
                    timestamp = msg.get('timestamp', '')
                    try:
                        bot.send_photo(
                            CHAT_HISTORIAL,
                            msg['file_id'],
                            caption=f"📸 Imagen de {nombre} ({timestamp})"
                        )
                    except Exception as e:
                        print(f"Error al enviar imagen: {e}")
                        bot.send_message(
                            CHAT_HISTORIAL,
                            f"❌ Error al enviar imagen de {nombre} ({timestamp})"
                        )
            
        except Exception as e:
            print(f"Error al enviar historial: {e}")
    
    # Notificar a ambas partes
    try:
        if tipo == "soporte":
            bot.send_message(chat_id, "✅ El agente de soporte ha cerrado el chat.\n¡Gracias por contactarnos!")
        elif tipo == "cliente":
            bot.send_message(chat_id, "✅ Has cerrado el chat.\n¡Gracias por contactarnos!")
            bot.send_message(CHAT_SOPORTE, f"❌ El cliente {conv['nombre_cliente']} (ID: {chat_id}) ha cerrado el chat.")
    except Exception as e:
        print(f"Error al enviar mensajes de cierre: {e}")
    
    # Limpiar datos
    del conversaciones_soporte[chat_id]

@bot.message_handler(commands=['cliente'])
def comando_cliente(message):
    """Maneja el comando /cliente"""
    if message.chat.id == CHAT_SOPORTE:
        bot.reply_to(message, "❌ Este comando solo puede ser usado por clientes.")
        return
    
    iniciar_chat_soporte(message)

@bot.message_handler(commands=['cerrar'])
def comando_cerrar(message):
    """Maneja el comando /cerrar"""
    chat_id = message.chat.id
    
    # Si es del chat de soporte
    if chat_id == CHAT_SOPORTE:
        # Buscar el cliente en conversación activa
        for cliente_id, conv in conversaciones_soporte.items():
            if conv.get('atendido'):
                cerrar_chat_soporte(cliente_id, "soporte")
                break
    # Si es del cliente
    elif chat_id in conversaciones_soporte:
        cerrar_chat_soporte(chat_id, "cliente")

@bot.callback_query_handler(func=lambda call: call.data.startswith('atender_soporte_'))
def atender_soporte(call):
    """Maneja el callback de atención de soporte"""
    # Verificar que el mensaje venga del chat de soporte
    if str(call.message.chat.id) != str(CHAT_SOPORTE):
        bot.answer_callback_query(call.id, "❌ No tienes permisos para atender chats")
        return
    
    chat_id = int(call.data.split('_')[2])
    if chat_id in conversaciones_soporte:
        conversaciones_soporte[chat_id]['atendido'] = True
        
        # Notificar al cliente
        bot.send_message(chat_id, "✅ Un agente de soporte te atenderá ahora.\nPuedes escribir tus mensajes.")
        
        # Notificar al chat de soporte
        bot.edit_message_reply_markup(
            chat_id=CHAT_SOPORTE,
            message_id=call.message.message_id,
            reply_markup=None
        )
        
        # Agregar botón para cerrar el chat
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "❌ Cerrar Chat",
            callback_data=f"cerrar_soporte_{chat_id}"
        ))
        
        bot.send_message(
            CHAT_SOPORTE,
            f"✅ Chat iniciado con cliente {conversaciones_soporte[chat_id]['nombre_cliente']} (ID: {chat_id})",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id, "✅ Chat atendido")

@bot.callback_query_handler(func=lambda call: call.data.startswith('cerrar_soporte_'))
def cerrar_soporte_callback(call):
    """Maneja el callback de cierre de chat desde soporte"""
    try:
        # Verificar que el mensaje venga del chat de soporte
        if str(call.message.chat.id) != str(CHAT_SOPORTE):
            bot.answer_callback_query(call.id, "❌ No tienes permisos para cerrar chats")
            return
        
        chat_id = int(call.data.split('_')[2])
        if chat_id in conversaciones_soporte:
            # Primero actualizar el markup para evitar el timeout
            bot.edit_message_reply_markup(
                chat_id=CHAT_SOPORTE,
                message_id=call.message.message_id,
                reply_markup=None
            )
            
            # Luego cerrar el chat
            cerrar_chat_soporte(chat_id, "soporte")
            
            # Finalmente responder al callback
            try:
                bot.answer_callback_query(call.id, "✅ Chat cerrado")
            except:
                pass  # Ignorar error de timeout en el callback
                
    except Exception as e:
        print(f"Error en cerrar_soporte_callback: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Error al cerrar el chat")
        except:
            pass

# Comando /start
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == ADMIN_CHAT_ID:
        # Mensaje para el administrador
        bot.reply_to(message, 
            "¡Bienvenido al Panel de Administración! 🎮\n\n"
            "Comandos disponibles:\n\n"
            "📊 Gestión de Rifas:\n"
            "/rifa - Comprar rifa\n"
            "/gratis - Obtener rifa gratis\n\n"
            "🎯 Comandos de Admin:\n"
            "/ganador - Elegir ganador de rifa pagada\n"
            "/ganadorz - Gestionar lista de ganadores\n"
            "/uno - Elegir ganador aleatorio de lista\n"
            "/pi - Elegir ganador de rifa gratis\n"
            "/qe - Gestionar links de páginas web\n"
            "/lista - Ver todas las listas de rifas\n"
            "/descargar - Descargar archivos JSON\n"
            "/borrar_historial - Gestionar historial\n"
            "/gods - Iniciar chat con cliente específico\n\n"
            "📈 Estadísticas y Soporte:\n"
            "/cliente - Ver chat de soporte\n"
            "👥 ID Admin: " + str(ADMIN_CHAT_ID))
    else:
        # Mensaje para clientes normales
        bot.reply_to(message, 
            "¡Bienvenido al Bot de Rifas! 🎉\n\n"
            "Comandos disponibles:\n\n"
            "🎫 Participación:\n"
            "/rifa - Comprar rifa\n"
            "/gratis - Obtener rifa gratis\n\n"
            "💬 Soporte:\n"
            "/cliente - Contactar con soporte\n\n"
            "¡Buena suerte! 🍀")

# Comando /rifa
@bot.message_handler(commands=['rifa'])
def rifa(message):
    chat_id = message.chat.id
    registro = cargar_datos(registro_collection, 'usuarios')
    
    # Verificar si el usuario ya está registrado
    usuario_existente = None
    if isinstance(registro, list):
        usuario_existente = next((u for u in registro if u.get('chat_id') == chat_id), None)
    
    if usuario_existente:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(usuario_existente.get('nombre', ''), "Otro")
        bot.send_message(chat_id, "¿Desea usar su nombre registrado o registrar uno nuevo?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_rifa)
    else:
        bot.send_message(chat_id, "Por favor, ingrese su nombre completo:")
        bot.register_next_step_handler(message, pedir_nombre_rifa)

def procesar_opcion_rifa(message):
    if message.text == "Otro":
        bot.send_message(message.chat.id, "Por favor, ingrese su nombre completo:")
        bot.register_next_step_handler(message, pedir_nombre_rifa)
    else:
        registro = cargar_datos(registro_collection, 'usuarios')
        usuario = None
        if isinstance(registro, list):
            usuario = next((u for u in registro if u.get('nombre') == message.text), None)
            
        if usuario:
            # Auto-rellenar celular y continuar con el proceso
            chat_id = message.chat.id
            
            # Enviar instrucciones de pago
            bot.send_message(chat_id, 
                f"Perfecto, {usuario.get('nombre', '')}.\n\n"
                "Por favor, proceda a depositar el monto correspondiente al número de boletos que desea adquirir:\n\n"
                "**Banco Pichincha**\n"
                "Cuenta de ahorro transaccional\n"
                "Número: 2209547823\n\n"
                "Ahora, envíame una foto del comprobante de pago.\n\n"
                "¡Gracias por su preferencia y apoyo!")
            
            bot.register_next_step_handler(message, procesar_comprobante_rifa, usuario.get('nombre', ''), usuario.get('celular', ''))
        else:
            bot.send_message(message.chat.id, "Usuario no encontrado. Por favor, ingrese su nombre completo:")
            bot.register_next_step_handler(message, pedir_nombre_rifa)

def pedir_nombre_rifa(message):
    if not message or not message.text:
        bot.send_message(message.chat.id, "Por favor, ingrese su nombre completo (nombre y apellido).")
        bot.register_next_step_handler(message, pedir_nombre_rifa)
        return
    
    nombre = message.text.strip()
    if len(nombre.split()) < 2:
        bot.send_message(message.chat.id, 
            "❌ Error: El nombre debe contener al menos nombre y apellido.\n\n"
            "Por favor, ingrese su nombre completo.\n"
            "Ejemplo: Juan Pérez")
        bot.register_next_step_handler(message, pedir_nombre_rifa)
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese su número de celular:")
        bot.register_next_step_handler(message, pedir_celular_rifa, nombre)

def pedir_celular_rifa(message, nombre):
    if not message or not message.text:
        bot.send_message(message.chat.id, "Por favor, ingrese su número de celular.")
        bot.register_next_step_handler(message, pedir_celular_rifa, nombre)
        return
    
    celular = message.text.strip()
    if not celular.isdigit():
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe contener solo dígitos.\n\n"
            "Por favor, ingrese su número de celular correctamente.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, pedir_celular_rifa, nombre)
    elif len(celular) < 10:
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe tener al menos 10 dígitos.\n\n"
            "Por favor, ingrese su número de celular completo.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, pedir_celular_rifa, nombre)
    else:
        chat_id = message.chat.id
        
        # Guardar en registro
        registro = cargar_datos(registro_collection, 'usuarios')
        
        # Eliminar cualquier registro existente con el mismo chat_id
        registro = [u for u in registro if u.get('chat_id') != chat_id]
        
        # Agregar el nuevo registro
        registro.append({
            'nombre': nombre,
            'celular': celular,
            'chat_id': chat_id,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_datos(registro_collection, registro, 'usuarios')
        
        # Enviar instrucciones de pago
        bot.send_message(chat_id, 
            f"✅ Perfecto, {nombre}.\n\n"
            "Por favor, proceda a depositar el monto correspondiente al número de boletos que desea adquirir:\n\n"
            "🏦 **Banco Pichincha**\n"
            "Cuenta de ahorro transaccional\n"
            "Número: 2209547823\n\n"
            "📸 Ahora, envíame una foto del comprobante de pago.\n\n"
            "¡Gracias por su preferencia y apoyo!")
        
        bot.register_next_step_handler(message, procesar_comprobante_rifa, nombre, celular)

def procesar_comprobante_rifa(message, nombre, celular):
    if not message:
        bot.send_message(message.chat.id, "Por favor, envíe una foto del comprobante de pago.")
        bot.register_next_step_handler(message, procesar_comprobante_rifa, nombre, celular)
        return
    
    if not message.photo:
        bot.send_message(message.chat.id, 
            "❌ Error: No se detectó una imagen.\n\n"
            "Por favor, envíe una foto clara del comprobante de pago.\n"
            "Asegúrese de que la imagen sea legible y muestre claramente el monto y la fecha.")
        bot.register_next_step_handler(message, procesar_comprobante_rifa, nombre, celular)
    else:
        # Generar un ID único para este comprobante
        comprobante_id = str(uuid.uuid4())
        
        # Enviar al admin para verificación con botones inline
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Sí", callback_data=f"verificar_si_{message.chat.id}_{comprobante_id}"),
            types.InlineKeyboardButton("❌ No", callback_data=f"verificar_no_{message.chat.id}_{comprobante_id}")
        )
        
        # Datos del nuevo comprobante
        nuevo_comprobante = {
            'nombre': nombre,
            'celular': celular,
            'chat_id': message.chat.id,
            'file_id': message.photo[-1].file_id,
            'comprobante_id': comprobante_id,
            'estado': 'pendiente',
            'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Obtener lista de comprobantes actual
        comprobantes = cargar_datos(comprobantes_pendientes_collection, 'comprobantes')
        
        # Añadir nuevo comprobante y guardar
        comprobantes.append(nuevo_comprobante)
        guardar_datos(comprobantes_pendientes_collection, comprobantes, 'comprobantes')
        
        # Enviar foto con botones al admin
        bot.send_photo(
            ADMIN_CHAT_ID,
            message.photo[-1].file_id,
            caption=f"📝 Verificar comprobante de:\nNombre: {nombre}\nCelular: {celular}\nID: {comprobante_id}",
            reply_markup=markup
        )
        
        # Mensaje al usuario
        bot.send_message(message.chat.id, 
            "✅ Tu comprobante ha sido enviado al administrador para verificación.\n\n"
            "📋 Proceso de verificación:\n"
            "1. El administrador revisará tu comprobante\n"
            "2. Si es válido, te pedirá la cantidad de boletos\n"
            "3. Recibirás tu código QR con los números\n\n"
            "⏳ Por favor, espera la respuesta del administrador.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('verificar_'))
def manejar_verificacion(call):
    if call.from_user.id == ADMIN_CHAT_ID:
        _, decision, chat_id, comprobante_id = call.data.split('_')
        chat_id = int(chat_id)
        
        # Obtener comprobantes pendientes
        comprobantes = cargar_datos(comprobantes_pendientes_collection, 'comprobantes')
        
        # Buscar el comprobante específico
        indice_comprobante = next((i for i, c in enumerate(comprobantes) if c['comprobante_id'] == comprobante_id), None)
        
        if indice_comprobante is not None:
            comprobante = comprobantes[indice_comprobante]
            
            if decision == 'si':
                # Actualizar estado del comprobante
                comprobantes[indice_comprobante]['estado'] = 'verificado'
                guardar_datos(comprobantes_pendientes_collection, comprobantes, 'comprobantes')
                
                bot.send_message(ADMIN_CHAT_ID, "¿Cuántos boletos está comprando?")
                bot.register_next_step_handler(call.message, procesar_cantidad_boletos, comprobante)
            else:
                # Actualizar estado del comprobante
                comprobantes[indice_comprobante]['estado'] = 'rechazado'
                guardar_datos(comprobantes_pendientes_collection, comprobantes, 'comprobantes')
                
                bot.send_message(comprobante['chat_id'], 
                    "Lo sentimos, su comprobante no fue verificado como auténtico. "
                    "Por favor, intente nuevamente con un comprobante válido.")
            
            # Actualizar mensaje original
            bot.edit_message_reply_markup(
                chat_id=ADMIN_CHAT_ID,
                message_id=call.message.message_id,
                reply_markup=None
            )
            
            # Mostrar mensaje de cuántos comprobantes quedan pendientes
            pendientes = sum(1 for c in comprobantes if c['estado'] == 'pendiente')
            if pendientes > 0:
                bot.send_message(ADMIN_CHAT_ID, f"Quedan {pendientes} comprobantes pendientes de verificar.")
    else:
        bot.answer_callback_query(call.id, "No tienes permisos para verificar comprobantes.")

def procesar_cantidad_boletos(message, datos_temp):
    if not message or not message.text:
        bot.send_message(ADMIN_CHAT_ID, "Por favor, ingrese la cantidad de boletos.")
        bot.register_next_step_handler(message, procesar_cantidad_boletos, datos_temp)
        return
    
    try:
        cantidad = int(message.text)
        if cantidad <= 0:
            bot.send_message(ADMIN_CHAT_ID, 
                "❌ Error: La cantidad debe ser mayor a 0.\n\n"
                "Por favor, ingrese una cantidad válida de boletos.\n"
                "Ejemplo: 1, 2, 3, etc.")
            bot.register_next_step_handler(message, procesar_cantidad_boletos, datos_temp)
        elif cantidad > 100:
            bot.send_message(ADMIN_CHAT_ID, 
                "❌ Error: La cantidad máxima es 100 boletos.\n\n"
                "Por favor, ingrese una cantidad válida de boletos.\n"
                "Ejemplo: 1, 2, 3, etc.")
            bot.register_next_step_handler(message, procesar_cantidad_boletos, datos_temp)
        else:
            # Generar números únicos
            numeros_unicos = [generar_numero_unico() for _ in range(cantidad)]
            
            # Guardar compra
            compras = cargar_datos(compras_collection, 'compras')
            compras.append({
                'nombre': datos_temp['nombre'],
                'celular': datos_temp['celular'],
                'chat_id': datos_temp['chat_id'],
                'cantidad': cantidad,
                'numeros_unicos': numeros_unicos,
                'fecha_compra': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'comprobante_id': datos_temp['comprobante_id']
            })
            guardar_datos(compras_collection, compras, 'compras')
            
            # Actualizar estado del comprobante a completado en la lista
            comprobantes = cargar_datos(comprobantes_pendientes_collection, 'comprobantes')
            indice_comprobante = next((i for i, c in enumerate(comprobantes) if c['comprobante_id'] == datos_temp['comprobante_id']), None)
            
            if indice_comprobante is not None:
                comprobantes[indice_comprobante]['estado'] = 'completado'
                guardar_datos(comprobantes_pendientes_collection, comprobantes, 'comprobantes')
            
            # Generar y enviar QR
            qr_data = f"Números Únicos:\n{', '.join(numeros_unicos)}\nNombre: {datos_temp['nombre']}\nCelular: {datos_temp['celular']}"
            qr_filename = f"qr_{datos_temp['chat_id']}.png"
            generar_qr(qr_data, qr_filename)
            
            with open(qr_filename, 'rb') as qr_file:
                bot.send_photo(datos_temp['chat_id'], qr_file)
            
            os.remove(qr_filename)
            
            # Mensaje de confirmación
            bot.send_message(datos_temp['chat_id'],
                f"🎉 ¡Gracias por tu compra, {datos_temp['nombre']}!\n\n"
                f"📋 Detalles de tu compra:\n"
                f"- Cantidad de boletos: {cantidad}\n"
                f"- Números únicos: {', '.join(numeros_unicos)}\n\n"
                "🎯 Tus números únicos están en el código QR adjunto.\n"
                "🍀 ¡Participa nuevamente para aumentar tus chances de ganar!")
    except ValueError:
        bot.send_message(ADMIN_CHAT_ID, 
            "❌ Error: Debe ingresar un número válido.\n\n"
            "Por favor, ingrese la cantidad de boletos usando solo números.\n"
            "Ejemplo: 1, 2, 3, etc.")
        bot.register_next_step_handler(message, procesar_cantidad_boletos, datos_temp)

# Comando /gratis
@bot.message_handler(commands=['gratis'])
def gratis(message):
    chat_id = message.chat.id
    
    # Verificar si el usuario ya participó hoy
    gratis = cargar_datos(gratis_collection, 'participantes')
    hoy = datetime.now().strftime('%Y-%m-%d')
    participacion_hoy = any(g['chat_id'] == chat_id and g['fecha_registro'].startswith(hoy) for g in gratis)
    
    if participacion_hoy:
        bot.send_message(chat_id, 
            "❌ Ya has participado hoy en la rifa gratis.\n\n"
            "Por favor, vuelve mañana para participar nuevamente.\n"
            "¡Gracias por tu interés! 🎉")
        return
    
    # Obtener links disponibles
    links = cargar_datos(links_collection, 'links')
    if not links:
        bot.send_message(chat_id, 
            "❌ Lo sentimos, no hay páginas disponibles en este momento.\n"
            "Por favor, intenta más tarde.")
        return
    
    # Enviar mensaje con los links disponibles
    mensaje = "🎉 Para obtener una rifa gratis, visita una de nuestras páginas web:\n\n"
    for i, link in enumerate(links, 1):
        mensaje += f"{i}. {link}\n"
    mensaje += "\nCopia el código que aparece en la página y envíalo aquí."
    
    bot.send_message(chat_id, mensaje)
    bot.register_next_step_handler(message, verificar_codigo_gratis)

def validar_codigo(codigo):
    """Valida un código y actualiza su estado"""
    try:
        # Cargar datos de la base de datos
        datos = codigos_collection.find_one()
        if not datos:
            print("Error: No se encontraron datos en la base de datos")
            return False
            
        # Verificar si el código está activo en la página 1
        codigos_activos = datos.get('codigos_activos', {})
        if codigos_activos.get('pagina1', {}).get('codigo') == codigo:
            return True
            
        return False
    except Exception as e:
        print(f"Error al validar código: {e}")
        return False

def verificar_codigo_gratis(message):
    try:
        chat_id = message.chat.id
        codigo = message.text.strip()
        
        # Validar el código
        if validar_codigo(codigo):
            # Verificar si el usuario ya está registrado
            registro = cargar_datos(registro_collection, 'usuarios')
            usuario_existente = None
            if isinstance(registro, list):
                usuario_existente = next((u for u in registro if u.get('chat_id') == chat_id), None)
            
            if usuario_existente:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(usuario_existente.get('nombre', ''), "Otro")
                bot.send_message(chat_id, "¿Desea usar su nombre registrado o registrar uno nuevo?", reply_markup=markup)
                bot.register_next_step_handler(message, procesar_opcion_gratis, codigo)
            else:
                bot.send_message(chat_id, "Por favor, ingrese su nombre completo:")
                bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)
        else:
            bot.send_message(chat_id, 
                "❌ Código no válido o expirado.\n"
                "Razones posibles:\n"
                "- El código no existe\n"
                "- El código ya está en uso\n"
                "- El código no está activo en la página 1\n\n"
                "Por favor, intente con otro código o visite nuestras páginas web para obtener uno nuevo.")
            bot.register_next_step_handler(message, verificar_codigo_gratis)
        
    except Exception as e:
        print(f"Error al verificar código: {e}")
        bot.send_message(chat_id, "❌ Error al verificar el código. Por favor, intente nuevamente.")
        bot.register_next_step_handler(message, verificar_codigo_gratis)

def procesar_opcion_gratis(message, codigo):
    if message.text == "Otro":
        bot.send_message(message.chat.id, "Por favor, ingrese su nombre completo:")
        bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)
    else:
        registro = cargar_datos(registro_collection, 'usuarios')
        usuario = None
        if isinstance(registro, list):
            usuario = next((u for u in registro if u.get('nombre') == message.text), None)
            
        if usuario:
            # Auto-rellenar celular y continuar con el proceso
            chat_id = message.chat.id
            nombre = usuario.get('nombre', '')
            celular = usuario.get('celular', '')
            
            # Generar número único
            numero_unico = generar_numero_unico()
            
            # Guardar en registro de rifas gratis
            gratis = cargar_datos(gratis_collection, 'participantes')
            gratis.append({
                'nombre': nombre,
                'celular': celular,
                'chat_id': chat_id,
                'numero_unico': numero_unico,
                'codigo': codigo,
                'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            guardar_datos(gratis_collection, gratis, 'participantes')
            
            # Generar y enviar QR
            qr_data = f"Número Único: {numero_unico}\nNombre: {nombre}\nCelular: {celular}"
            qr_filename = f"qr_gratis_{chat_id}.png"
            generar_qr(qr_data, qr_filename)
            
            with open(qr_filename, 'rb') as qr_file:
                bot.send_photo(chat_id, qr_file)
            
            os.remove(qr_filename)
            
            # Mensaje de confirmación
            bot.send_message(chat_id,
                f"¡Felicidades, {nombre}! 🎉\n\n"
                "Has obtenido una rifa gratis.\n"
                "Tu número único está en el código QR adjunto.\n\n"
                "¡Buena suerte! 🍀")
        else:
            bot.send_message(message.chat.id, "Usuario no encontrado. Por favor, ingrese su nombre completo:")
            bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)

def pedir_nombre_gratis(message, codigo):
    if not message or not message.text:
        bot.send_message(message.chat.id, "Por favor, ingrese su nombre completo (nombre y apellido).")
        bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)
        return
    
    nombre = message.text.strip()
    if len(nombre.split()) < 2:
        bot.send_message(message.chat.id, 
            "❌ Error: El nombre debe contener al menos nombre y apellido.\n\n"
            "Por favor, ingrese su nombre completo.\n"
            "Ejemplo: Juan Pérez")
        bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese su número de celular:")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)

def pedir_celular_gratis(message, nombre, codigo):
    if not message or not message.text:
        bot.send_message(message.chat.id, "Por favor, ingrese su número de celular.")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)
        return
    
    celular = message.text.strip()
    if not celular.isdigit():
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe contener solo dígitos.\n\n"
            "Por favor, ingrese su número de celular correctamente.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)
    elif len(celular) < 10:
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe tener al menos 10 dígitos.\n\n"
            "Por favor, ingrese su número de celular completo.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)
    else:
        chat_id = message.chat.id
        
        # Guardar en registro
        registro = cargar_datos(registro_collection, 'usuarios')
        
        # Eliminar cualquier registro existente con el mismo chat_id
        registro = [u for u in registro if u.get('chat_id') != chat_id]
        
        # Agregar el nuevo registro
        registro.append({
            'nombre': nombre,
            'celular': celular,
            'chat_id': chat_id,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_datos(registro_collection, registro, 'usuarios')
        
        # Generar número único
        numero_unico = generar_numero_unico()
        
        # Guardar en registro de rifas gratis
        gratis = cargar_datos(gratis_collection, 'participantes')
        gratis.append({
            'nombre': nombre,
            'celular': celular,
            'chat_id': chat_id,
            'numero_unico': numero_unico,
            'codigo': codigo,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_datos(gratis_collection, gratis, 'participantes')
        
        # Generar y enviar QR
        qr_data = f"Número Único: {numero_unico}\nNombre: {nombre}\nCelular: {celular}"
        qr_filename = f"qr_gratis_{chat_id}.png"
        generar_qr(qr_data, qr_filename)
        
        with open(qr_filename, 'rb') as qr_file:
            bot.send_photo(chat_id, qr_file)
        
        os.remove(qr_filename)
        
        # Mensaje de confirmación
        bot.send_message(chat_id,
            f"¡Felicidades, {nombre}! 🎉\n\n"
            "Has obtenido una rifa gratis.\n"
            "Tu número único está en el código QR adjunto.\n\n"
            "¡Buena suerte! 🍀")

# Comando /lista (solo admin)
@bot.message_handler(commands=['lista'])
def lista(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Rifas Pagadas", "Rifas Gratis", "Ganadores", "Historial Pagas", "Historial Gratis")
        bot.send_message(message.chat.id, "¿Qué lista desea ver?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_lista)
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

def procesar_opcion_lista(message):
    if not message or not message.text:
        return
    
    if message.text == "Rifas Pagadas":
        compras = cargar_datos(compras_collection, 'compras')
        if compras:
            lista = "\n".join([
                f"{i+1}. {c['nombre']} - {c['celular']} - {c['cantidad']} boletos"
                for i, c in enumerate(compras)
            ])
            bot.send_message(message.chat.id, f"📋 Lista de Rifas Pagadas:\n\n{lista}")
        else:
            bot.send_message(message.chat.id, "No hay rifas pagadas registradas.")
    
    elif message.text == "Rifas Gratis":
        gratis = cargar_datos(gratis_collection, 'participantes')
        if gratis:
            lista = "\n".join([
                f"{i+1}. {g['nombre']} - {g['celular']}"
                for i, g in enumerate(gratis)
            ])
            bot.send_message(message.chat.id, f"📋 Lista de Rifas Gratis:\n\n{lista}")
        else:
            bot.send_message(message.chat.id, "No hay rifas gratis registradas.")
    
    elif message.text == "Ganadores":
        ganadores = cargar_datos(ganadores_collection, 'ganadores')
        if ganadores:
            lista = "\n".join([
                f"{i+1}. {g['nombre']} - {g['celular']}"
                for i, g in enumerate(ganadores)
            ])
            bot.send_message(message.chat.id, f"🏆 Lista de Ganadores:\n\n{lista}")
        else:
            bot.send_message(message.chat.id, "No hay ganadores registrados.")
    
    elif message.text == "Historial Pagas":
        historial = cargar_datos(historial_rifa_collection, 'historial')
        if historial:
            mensaje = "📋 Historial de Rifas Pagadas:\n\n"
            for fecha, compras in historial.items():
                mensaje += f"📅 Fecha: {fecha}\n"
                for i, c in enumerate(compras, 1):
                    mensaje += f"  {i}. {c['nombre']} - {c['celular']} - {c['cantidad']} boletos\n"
                mensaje += "\n"
            bot.send_message(message.chat.id, mensaje)
        else:
            bot.send_message(message.chat.id, "No hay historial de rifas pagadas.")
    
    elif message.text == "Historial Gratis":
        historial = cargar_datos(historial_gratis_collection, 'historial')
        if historial:
            mensaje = "📋 Historial de Rifas Gratis:\n\n"
            for fecha, participantes in historial.items():
                mensaje += f"📅 Fecha: {fecha}\n"
                for i, p in enumerate(participantes, 1):
                    mensaje += f"  {i}. {p['nombre']} - {p['celular']}\n"
                mensaje += "\n"
            bot.send_message(message.chat.id, mensaje)
        else:
            bot.send_message(message.chat.id, "No hay historial de rifas gratis.")

# Comando /descargar (solo admin)
@bot.message_handler(commands=['descargar'])
def descargar(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Registro", "Compras", "Ganadores", "Gratis", "Códigos", "Links", "Historial Pagas", "Historial Gratis")
        bot.send_message(message.chat.id, "¿Qué archivo desea descargar?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_descargar)
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

def procesar_opcion_descargar(message):
    if not message or not message.text:
        return
    
    try:
        # Crear directorio temporal si no existe
        if not os.path.exists('temp'):
            os.makedirs('temp')
        
        # Obtener datos según la opción seleccionada
        if message.text == "Registro":
            datos = cargar_datos(registro_collection)
            archivo = 'temp/registro.json'
        elif message.text == "Compras":
            datos = cargar_datos(compras_collection, 'compras')
            archivo = 'temp/compras.json'
        elif message.text == "Ganadores":
            datos = cargar_datos(ganadores_collection, 'ganadores')
            archivo = 'temp/ganadores.json'
        elif message.text == "Gratis":
            datos = cargar_datos(gratis_collection, 'participantes')
            archivo = 'temp/gratis.json'
        elif message.text == "Códigos":
            datos = cargar_datos(codigos_collection)
            archivo = 'temp/codigos.json'
        elif message.text == "Links":
            datos = cargar_datos(links_collection, 'links')
            archivo = 'temp/links.json'
        elif message.text == "Historial Pagas":
            datos = cargar_datos(historial_rifa_collection, 'historial')
            archivo = 'temp/historial_pagas.json'
        elif message.text == "Historial Gratis":
            datos = cargar_datos(historial_gratis_collection, 'historial')
            archivo = 'temp/historial_gratis.json'
        else:
            bot.send_message(message.chat.id, "❌ Opción no válida.")
            return
        
        # Guardar datos en archivo temporal
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        
        # Enviar archivo
        with open(archivo, 'rb') as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"📥 Archivo {message.text} descargado exitosamente."
            )
        
        # Eliminar archivo temporal
        os.remove(archivo)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error al descargar el archivo: {str(e)}")

# Comando /borrar_historial (solo admin)
@bot.message_handler(commands=['borrar_historial'])
def borrar_historial(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Rifas Pagadas", "Rifas Gratis", "Historial Pagas", "Historial Gratis", "Registros", "Todo")
        bot.send_message(message.chat.id, "¿Qué historial desea borrar?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_borrar)
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

def procesar_opcion_borrar(message):
    if not message or not message.text:
        return
    
    try:
        if message.text == "Rifas Pagadas":
            # Mover datos actuales al historial
            compras = cargar_datos(compras_collection, 'compras')
            historial_rifas = cargar_datos(historial_rifa_collection, 'historial')
            fecha_actual = datetime.now().strftime('%Y-%m-%d')
            
            if compras:
                # Verificar si ya existe un historial para esta fecha
                if fecha_actual in historial_rifas:
                    # Si existe, agregar los nuevos datos a los existentes
                    historial_rifas[fecha_actual].extend(compras)
                else:
                    # Si no existe, crear una nueva entrada
                    historial_rifas[fecha_actual] = compras
                
                guardar_datos(historial_rifa_collection, historial_rifas, 'historial')
                guardar_datos(compras_collection, [], 'compras')
                bot.send_message(message.chat.id, "✅ Historial de rifas pagadas borrado exitosamente.")
            else:
                bot.send_message(message.chat.id, "No hay datos de rifas pagadas para borrar.")
        
        elif message.text == "Rifas Gratis":
            # Mover datos actuales al historial
            gratis = cargar_datos(gratis_collection, 'participantes')
            historial_gratis = cargar_datos(historial_gratis_collection, 'historial')
            fecha_actual = datetime.now().strftime('%Y-%m-%d')
            
            if gratis:
                # Verificar si ya existe un historial para esta fecha
                if fecha_actual in historial_gratis:
                    # Si existe, agregar los nuevos datos a los existentes
                    historial_gratis[fecha_actual].extend(gratis)
                else:
                    # Si no existe, crear una nueva entrada
                    historial_gratis[fecha_actual] = gratis
                
                guardar_datos(historial_gratis_collection, historial_gratis, 'historial')
                guardar_datos(gratis_collection, [], 'participantes')
                bot.send_message(message.chat.id, "✅ Historial de rifas gratis borrado exitosamente.")
            else:
                bot.send_message(message.chat.id, "No hay datos de rifas gratis para borrar.")
        
        elif message.text == "Historial Pagas":
            # Borrar historial de rifas pagadas completamente
            guardar_datos(historial_rifa_collection, {'historial': {}}, 'historial')
            bot.send_message(message.chat.id, "✅ Historial de pagas borrado exitosamente.")
        
        elif message.text == "Historial Gratis":
            # Borrar historial de rifas gratis completamente
            guardar_datos(historial_gratis_collection, {'historial': {}}, 'historial')
            bot.send_message(message.chat.id, "✅ Historial de gratis borrado exitosamente.")
        
        elif message.text == "Registros":
            # Borrar registros de usuarios
            guardar_datos(registro_collection, {'usuarios': []}, 'usuarios')
            bot.send_message(message.chat.id, "✅ Registros de usuarios borrados exitosamente.")
        
        elif message.text == "Todo":
            # Mover todos los datos al historial
            mover_datos_a_historial()
            bot.send_message(message.chat.id, "✅ Todo el historial ha sido borrado exitosamente.")
        
        else:
            bot.send_message(message.chat.id, "❌ Opción no válida.")
    
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error al borrar el historial: {str(e)}")

# Comando /qe (solo admin)
@bot.message_handler(commands=['qe'])
def qe(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Agregar Link", "Eliminar Link", "Ver Links")
        bot.send_message(message.chat.id, "¿Qué desea hacer con los links?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_qe)
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

def procesar_opcion_qe(message):
    if not message or not message.text:
        return
    if message.text == "Agregar Link":
        bot.send_message(message.chat.id, "Por favor, envíe el link completo (ejemplo: https://ejemplo.com):")
        bot.register_next_step_handler(message, agregar_link)
    elif message.text == "Eliminar Link":
        links = cargar_datos(links_collection, 'links')
        if links:
            lista = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links)])
            bot.send_message(message.chat.id, f"Seleccione el número del link a eliminar:\n\n{lista}")
            bot.register_next_step_handler(message, eliminar_link)
        else:
            bot.send_message(message.chat.id, "No hay links registrados.")
    elif message.text == "Ver Links":
        links = cargar_datos(links_collection, 'links')
        if links:
            lista = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links)])
            bot.send_message(message.chat.id, f"Lista de links:\n\n{lista}")
        else:
            bot.send_message(message.chat.id, "No hay links registrados.")

def agregar_link(message):
    if not message or not message.text:
        return
    link = message.text.strip()
    if link.startswith('http://') or link.startswith('https://'):
        links = cargar_datos(links_collection, 'links')
        if link not in links:
            links.append(link)
            guardar_datos(links_collection, links, 'links')
            bot.send_message(message.chat.id, "✅ Link agregado exitosamente.")
        else:
            bot.send_message(message.chat.id, "❌ Este link ya está registrado.")
    else:
        bot.send_message(message.chat.id, "❌ Por favor, envíe un link válido que comience con http:// o https://")

def eliminar_link(message):
    if not message or not message.text:
        return
    try:
        indice = int(message.text) - 1
        links = cargar_datos(links_collection, 'links')
        if 0 <= indice < len(links):
            link_eliminado = links.pop(indice)
            guardar_datos(links_collection, links, 'links')
            bot.send_message(message.chat.id, f"✅ Link '{link_eliminado}' eliminado exitosamente.")
        else:
            bot.send_message(message.chat.id, "❌ Número de link no válido.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Por favor, ingrese un número válido.")

# Comando /pi (solo admin)
@bot.message_handler(commands=['pi'])
def pi(message):
    if message.chat.id == ADMIN_CHAT_ID:
        participantes = cargar_datos(gratis_collection, 'participantes')
        if participantes:
            # Elegir ganador aleatorio
            ganador = random.choice(participantes)
            
            # Notificar al admin
            bot.send_message(ADMIN_CHAT_ID,
                f"🎉 ¡Ganador de rifa gratuita seleccionado!\n\n"
                f"👤 Nombre: {ganador['nombre']}\n"
                f"📱 Celular: {ganador['celular']}\n"
                f"🎫 Número único: {ganador['numero_unico']}")
            
            # Notificar al ganador
            bot.send_message(ganador['chat_id'],
                f"🎉 ¡Felicidades, {ganador['nombre']}! 🎉\n\n"
                "Has sido seleccionado como ganador de la rifa gratuita.\n"
                "Nos pondremos en contacto contigo pronto para coordinar la entrega de tu premio. 🏆")
            
            # Notificar a los demás participantes
            mensaje_participantes = (
                f"🎯 ¡Tenemos un ganador!\n\n"
                f"Felicitaciones a {ganador['nombre']}, quien ganó con el número único {ganador['numero_unico']}.\n\n"
                "No te desanimes, ¡la próxima semana podrías ser tú!\n"
                "Tenemos grandes sorpresas preparadas para los próximos sorteos. 🎁\n\n"
                "Usa /gratis para participar en el próximo sorteo. 🍀"
            )
            
            for participante in participantes:
                if participante['chat_id'] != ganador['chat_id']:
                    try:
                        bot.send_message(participante['chat_id'], mensaje_participantes)
                    except:
                        continue
            
            # Enviar mensaje global a todos los registros
            registro = cargar_datos(registro_collection, 'usuarios')
            mensaje_global = (
                f"🎉 ¡Nuevo ganador de rifa gratuita! 🎉\n\n"
                f"Felicitaciones a {ganador['nombre']} por ganar la rifa gratuita de esta semana.\n\n"
                "¡Comienza una nueva acumulación!\n"
                "No pierdas la oportunidad de participar en el próximo sorteo.\n"
                "Cada boleto aumenta tus posibilidades de ganar.\n\n"
                "🎁 Premios increíbles te esperan:\n"
                "• Grandes premios en efectivo\n"
                "• Productos exclusivos\n"
                "• Experiencias únicas\n\n"
                "Usa /gratis para participar sin costo.\n"
                "¡No te quedes fuera de la próxima rifa! 🍀"
            )
            
            for usuario in registro:
                try:
                    bot.send_message(usuario['chat_id'], mensaje_global)
                except:
                    continue
            
            # Guardar en historial de ganadores
            ganadores = cargar_datos(ganadores_collection, 'ganadores')
            ganadores.append({
                'nombre': ganador['nombre'],
                'celular': ganador['celular'],
                'chat_id': ganador['chat_id'],
                'tipo': 'gratis',
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            guardar_datos(ganadores_collection, ganadores, 'ganadores')
            
            # Mover datos actuales al historial
            historial_gratis = cargar_datos(historial_gratis_collection, 'historial')
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if participantes:
                # Verificar si ya existe un historial para esta fecha
                if fecha_actual in historial_gratis:
                    # Si existe, agregar los nuevos datos a los existentes
                    historial_gratis[fecha_actual].extend(participantes)
                else:
                    # Si no existe, crear una nueva entrada
                    historial_gratis[fecha_actual] = participantes
                
                guardar_datos(historial_gratis_collection, historial_gratis, 'historial')
                guardar_datos(gratis_collection, [], 'participantes')
        else:
            bot.send_message(ADMIN_CHAT_ID, "❌ No hay participantes en rifas gratis registrados.")
    else:
        bot.send_message(message.chat.id, "❌ No tienes permisos para usar este comando.")

# Comando /ganador (solo admin)
@bot.message_handler(commands=['ganador'])
def ganador(message):
    if message.chat.id == ADMIN_CHAT_ID:
        compras = cargar_datos(compras_collection, 'compras')
        if compras:
            # Elegir ganador aleatorio
            ganador = random.choice(compras)
            
            # Notificar al admin
            bot.send_message(ADMIN_CHAT_ID,
                f"🎉 ¡Ganador de rifa pagada seleccionado!\n\n"
                f"👤 Nombre: {ganador['nombre']}\n"
                f"📱 Celular: {ganador['celular']}\n"
                f"🎫 Número único: {', '.join(ganador['numeros_unicos'])}")
            
            # Notificar al ganador
            bot.send_message(ganador['chat_id'],
                f"🎉 ¡Felicidades, {ganador['nombre']}! 🎉\n\n"
                "Has sido seleccionado como ganador de la rifa.\n"
                "Nos pondremos en contacto contigo pronto para coordinar la entrega de tu premio. 🏆")
            
            # Notificar a los demás participantes
            mensaje_participantes = (
                f"🎯 ¡Tenemos un ganador!\n\n"
                f"Felicitaciones a {ganador['nombre']}, quien ganó con {ganador.get('cantidad', 1)} boleto(s).\n\n"
                "No te desanimes, ¡la próxima semana podrías ser tú!\n"
                "Tenemos grandes sorpresas preparadas para los próximos sorteos. 🎁\n\n"
                "Usa /rifa o /gratis para participar en el próximo sorteo. 🍀"
            )
            
            for participante in compras:
                if participante['chat_id'] != ganador['chat_id']:
                    try:
                        bot.send_message(participante['chat_id'], mensaje_participantes)
                    except:
                        continue
            
            # Enviar mensaje global a todos los registros
            registro = cargar_datos(registro_collection, 'usuarios')
            mensaje_global = (
                f"🎉 ¡Nuevo ganador de rifa! 🎉\n\n"
                f"Felicitaciones a {ganador['nombre']} por ganar la rifa de esta semana.\n\n"
                "¡Comienza una nueva acumulación!\n"
                "No pierdas la oportunidad de participar en el próximo sorteo.\n"
                "Cada boleto aumenta tus posibilidades de ganar.\n\n"
                "🎁 Premios increíbles te esperan:\n"
                "• Grandes premios en efectivo\n"
                "• Productos exclusivos\n"
                "• Experiencias únicas\n\n"
                "Usa /rifa para comprar tus boletos o /gratis para participar sin costo.\n"
                "¡No te quedes fuera de la próxima rifa! 🍀"
            )
            
            for usuario in registro:
                try:
                    bot.send_message(usuario['chat_id'], mensaje_global)
                except:
                    continue
            
            # Guardar en historial de ganadores
            ganadores = cargar_datos(ganadores_collection, 'ganadores')
            ganadores.append({
                'nombre': ganador['nombre'],
                'celular': ganador['celular'],
                'chat_id': ganador['chat_id'],
                'tipo': 'pagada',
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            guardar_datos(ganadores_collection, ganadores, 'ganadores')
            
            # Mover datos actuales al historial
            historial_rifas = cargar_datos(historial_rifa_collection, 'historial')
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if compras:
                # Verificar si ya existe un historial para esta fecha
                if fecha_actual in historial_rifas:
                    # Si existe, agregar los nuevos datos a los existentes
                    historial_rifas[fecha_actual].extend(compras)
                else:
                    # Si no existe, crear una nueva entrada
                    historial_rifas[fecha_actual] = compras
                
                guardar_datos(historial_rifa_collection, historial_rifas, 'historial')
                guardar_datos(compras_collection, [], 'compras')
        else:
            bot.send_message(ADMIN_CHAT_ID, "❌ No hay participantes en rifas pagadas registrados.")
    else:
        bot.send_message(message.chat.id, "❌ No tienes permisos para usar este comando.")

# Comando /ganadorz (solo admin)
@bot.message_handler(commands=['ganadorz'])
def ganadorz(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Agregar", "Eliminar", "Ver lista")
        bot.send_message(message.chat.id, "¿Qué desea hacer?", reply_markup=markup)
        bot.register_next_step_handler(message, procesar_opcion_ganadorz)
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

def procesar_opcion_ganadorz(message):
    """Procesa las opciones del comando /ganadorz para gestionar la lista de ganadores"""
    if not message or not message.text:
        return
    
    try:
        if message.text == "Agregar":
            # Solicitar nombre del ganador
            bot.send_message(message.chat.id, "Por favor, ingrese el nombre completo del ganador:")
            bot.register_next_step_handler(message, agregar_ganador_nombre)
        
        elif message.text == "Eliminar":
            # Mostrar lista de ganadores para eliminar
            ganadores = cargar_datos(ganadores_collection, 'ganadores')
            if ganadores:
                lista = "\n".join([
                    f"{i+1}. {g['nombre']} - {g['celular']}"
                    for i, g in enumerate(ganadores)
                ])
                bot.send_message(message.chat.id, 
                    "Seleccione el número del ganador a eliminar:\n\n" + lista)
                bot.register_next_step_handler(message, eliminar_ganador)
            else:
                bot.send_message(message.chat.id, "No hay ganadores registrados.")
        
        elif message.text == "Ver lista":
            # Mostrar lista de ganadores
            ganadores = cargar_datos(ganadores_collection, 'ganadores')
            if ganadores:
                lista = "\n".join([
                    f"{i+1}. {g['nombre']} - {g['celular']} - {g['tipo']} - {g['fecha']}"
                    for i, g in enumerate(ganadores)
                ])
                bot.send_message(message.chat.id, f"📋 Lista de Ganadores:\n\n{lista}")
            else:
                bot.send_message(message.chat.id, "No hay ganadores registrados.")
        
        else:
            bot.send_message(message.chat.id, "❌ Opción no válida.")
    
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def agregar_ganador_nombre(message):
    """Procesa el nombre del ganador para agregar"""
    if not message or not message.text:
        return
    
    nombre = message.text.strip()
    if len(nombre.split()) < 2:
        bot.send_message(message.chat.id, 
            "❌ Error: El nombre debe contener al menos nombre y apellido.\n\n"
            "Por favor, ingrese su nombre completo.\n"
            "Ejemplo: Juan Pérez")
        bot.register_next_step_handler(message, agregar_ganador_nombre)
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese el número de celular del ganador:")
        bot.register_next_step_handler(message, agregar_ganador_celular, nombre)

def agregar_ganador_celular(message, nombre):
    """Procesa el celular del ganador para agregar"""
    if not message or not message.text:
        return
    
    celular = message.text.strip()
    if not celular.isdigit():
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe contener solo dígitos.\n\n"
            "Por favor, ingrese el número de celular correctamente.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, agregar_ganador_celular, nombre)
    elif len(celular) < 10:
        bot.send_message(message.chat.id, 
            "❌ Error: El número de celular debe tener al menos 10 dígitos.\n\n"
            "Por favor, ingrese el número de celular completo.\n"
            "Ejemplo: 0991234567")
        bot.register_next_step_handler(message, agregar_ganador_celular, nombre)
    else:
        # Guardar ganador
        ganadores = cargar_datos(ganadores_collection, 'ganadores')
        ganadores.append({
            'nombre': nombre,
            'celular': celular,
            'tipo': 'manual',
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_datos(ganadores_collection, ganadores, 'ganadores')
        
        bot.send_message(message.chat.id, 
            f"✅ Ganador agregado exitosamente:\n\n"
            f"👤 Nombre: {nombre}\n"
            f"📱 Celular: {celular}")

def eliminar_ganador(message):
    """Procesa la eliminación de un ganador"""
    if not message or not message.text:
        return
    
    try:
        indice = int(message.text) - 1
        ganadores = cargar_datos(ganadores_collection, 'ganadores')
        if 0 <= indice < len(ganadores):
            ganador_eliminado = ganadores.pop(indice)
            guardar_datos(ganadores_collection, ganadores, 'ganadores')
            bot.send_message(message.chat.id, 
                f"✅ Ganador eliminado exitosamente:\n\n"
                f"👤 Nombre: {ganador_eliminado['nombre']}\n"
                f"📱 Celular: {ganador_eliminado['celular']}")
        else:
            bot.send_message(message.chat.id, "❌ Número de ganador no válido.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Por favor, ingrese un número válido.")

@bot.message_handler(commands=['gods'])
def comando_gods(message):
    try:
        # Verificar que sea el CHAT_OPERADOR
        if message.chat.id != CHAT_OPERADOR:
            bot.reply_to(message, "❌ No tienes permisos para usar este comando")
            return
        
        # Solicitar ID del cliente
        msg = bot.send_message(
            CHAT_OPERADOR,
            "📝 Por favor, envía el ID del cliente para iniciar el chat"
        )
        bot.register_next_step_handler(msg, iniciar_chat_gods)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def iniciar_chat_gods(message):
    try:
        # Verificar que el mensaje venga del CHAT_OPERADOR
        if message.chat.id != CHAT_OPERADOR:
            bot.reply_to(message, "❌ No tienes permisos para usar este comando")
            return

        # Convertir el ID a número
        cliente_id = int(message.text)
        
        # Verificar si el cliente ya está en una conversación
        if cliente_id in conversaciones_activas:
            bot.reply_to(message, "❌ Este cliente ya está en una conversación")
            return
        
        # Iniciar la conversación
        conversaciones_activas[cliente_id] = {
            'inicio': datetime.now(),
            'mensajes': [],
            'atendido': True,
            'tipo': 'gods'  # Marcar que es una conversación de tipo gods
        }
        
        # Notificar al CHAT_OPERADOR
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "❌ Cerrar Chat Gods",
            callback_data=f"cerrar_gods_{cliente_id}"
        ))
        
        bot.send_message(
            CHAT_OPERADOR,
            f"✅ Chat iniciado con cliente {cliente_id}\n"
            "📝 Puedes empezar a escribir mensajes\n"
            "❌ Para cerrar el chat usa el botón de abajo",
            reply_markup=markup
        )
        
        # Notificar al cliente
        try:
            bot.send_message(
                cliente_id,
                "👨‍💼 Un agente de soporte ha iniciado una conversación\n"
                "✍️ Puedes escribir tus mensajes"
            )
        except Exception as e:
            bot.reply_to(
                message,
                f"⚠️ No se pudo notificar al cliente: {str(e)}\n"
                "El chat sigue activo."
            )
            
    except ValueError:
        bot.reply_to(
            message,
            "❌ Error: El ID debe ser un número\n"
            "Por favor, intenta nuevamente con /gods"
        )
    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Error inesperado: {str(e)}\n"
            "Por favor, intenta nuevamente con /gods"
        )

@bot.message_handler(commands=['cortar'])
def cortar_chat(message):
    try:
        # Verificar que sea el CHAT_OPERADOR
        if message.chat.id != CHAT_OPERADOR:
            bot.reply_to(message, "❌ No tienes permisos para usar este comando")
        return

        # Buscar conversación activa
        chat_activo = obtener_conversacion_activa_operador(CHAT_OPERADOR)
        if chat_activo:
            cerrar_conversacion(chat_activo, "operador")
            bot.reply_to(message, "✅ Chat cerrado exitosamente")
        else:
            bot.reply_to(message, "❌ No hay ningún chat activo para cerrar")

    except Exception as e:
        bot.reply_to(message, f"❌ Error al cerrar el chat: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if call.data.startswith("cerrar_gods_"):
            # Verificar que sea el CHAT_OPERADOR
            if call.from_user.id != CHAT_OPERADOR:
                bot.answer_callback_query(call.id, "❌ No tienes permisos para cerrar chats")
                return  # Mover el return aquí

            # Operador quiere cerrar el chat
            chat_id = int(call.data.split("_")[2])
            if chat_id in conversaciones_activas and conversaciones_activas[chat_id].get('tipo') == 'gods':
                cerrar_conversacion(chat_id, "operador")
                bot.answer_callback_query(call.id, "✅ Chat cerrado")
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error al procesar la acción")
        print(f"Error en callback: {e}")

def obtener_conversacion_activa_operador(chat_id):
    """Busca si hay una conversación activa para el chat especificado"""
    for conv_id, conversacion in conversaciones_activas.items():
        if conversacion.get('atendido') and conversacion.get('tipo') == 'gods' and chat_id == CHAT_OPERADOR:
            return conv_id
    return None

def procesar_mensaje_cliente(message):
    chat_id = message.chat.id
    if chat_id not in conversaciones_activas:
        return

    # Verificar si la conversación está atendida
    conversacion = conversaciones_activas[chat_id]
    if not conversacion.get('atendido'):
        return  # No procesar mensajes si no está atendido

    # Asegurarse de que 'mensajes' sea una lista
    if 'mensajes' not in conversacion:
        conversacion['mensajes'] = []
    elif not isinstance(conversacion['mensajes'], list):
        conversacion['mensajes'] = []

    # Guardar mensaje
    conversacion['mensajes'].append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'from_id': chat_id,
        'nombre': message.from_user.first_name,
        'content': message.text if message.text else '[imagen]',
        'type': 'text' if message.text else 'image'
    })

    # Enviar al CHAT_OPERADOR
    try:
        if conversacion.get('tipo') == 'gods':
            # Para chats de tipo gods, enviar al CHAT_OPERADOR
            if message.text:
                bot.send_message(CHAT_OPERADOR, f"👤 Cliente {message.from_user.first_name} (ID: {chat_id}):\n{message.text}")
            elif message.photo:
                bot.send_photo(CHAT_OPERADOR, message.photo[-1].file_id, caption=f"📸 Imagen de {message.from_user.first_name} (ID: {chat_id})")
    except Exception as e:
        print(f"Error al enviar mensaje al operador: {e}")

# Manejador para mensajes normales
@bot.message_handler(content_types=['text', 'photo'])
def manejar_mensajes(message):
    # Procesar mensajes de soporte
    procesar_mensaje_soporte(message)
    
    # Si es un mensaje del CHAT_OPERADOR
    if message.chat.id == CHAT_OPERADOR:
        # Buscar si hay un cliente en conversación
        for chat_id, conversacion in conversaciones_activas.items():
            try:
                # Verificar si la conversación está atendida y es de tipo gods
                if not conversacion.get('atendido') or conversacion.get('tipo') != 'gods':
                    continue  # Saltar a la siguiente conversación si no es la atendida

                # Asegurarse de que 'mensajes' sea una lista
                if 'mensajes' not in conversacion:
                    conversacion['mensajes'] = []
                elif not isinstance(conversacion['mensajes'], list):
                    conversacion['mensajes'] = []

                # Guardar mensaje
                conversacion['mensajes'].append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'from_id': CHAT_OPERADOR,
                    'content': message.text if message.text else '[imagen]',
                    'type': 'text' if message.text else 'image'
                })
                
                # Enviar al cliente
                if message.text and not message.text.startswith('/'):
                    bot.send_message(chat_id, f"👨‍💼 Operador: {message.text}")
                elif message.photo:
                    bot.send_photo(chat_id, message.photo[-1].file_id, caption="👨‍💼 Imagen del operador")
                break  # Solo procesar la conversación atendida
            except Exception as e:
                print(f"Error al enviar mensaje al cliente: {e}")
    
    # Si es un mensaje del cliente
    elif message.chat.id in conversaciones_activas:
        procesar_mensaje_cliente(message)

def cerrar_conversacion(chat_id, tipo):
    """Cierra una conversación y limpia los datos asociados"""
    if chat_id not in conversaciones_activas:
        return

    conversacion = conversaciones_activas[chat_id]

    # Asegurarse de que 'mensajes' sea una lista
    if 'mensajes' not in conversacion:
        conversacion['mensajes'] = []
    elif not isinstance(conversacion['mensajes'], list):
        conversacion['mensajes'] = []

    # Obtener el historial de la conversación
    historial = conversacion['mensajes']
    if historial:
        # Crear mensaje principal con la información del cliente
        cliente_info = f"📝 Historial de conversación\n\n"
        cliente_info += f"🆔 ID del Chat: {chat_id}\n"
        cliente_info += f"⏰ Inicio: {conversacion['inicio'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        cliente_info += f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        cliente_info += f"📋 Tipo: {conversacion.get('tipo', 'desconocido')}\n"
        cliente_info += f"👤 Operador: {'Atendido' if conversacion.get('atendido') else 'No atendido'}\n\n"
        cliente_info += "💬 Mensajes:\n\n"

        # Separar mensajes de texto e imágenes
        mensajes_texto = []
        imagenes = []
        
        for msg in historial:
            if msg['type'] == 'text':
                mensajes_texto.append(msg)
            elif msg['type'] == 'image':
                imagenes.append(msg)

        # Enviar mensaje principal con la información
        try:
            bot.send_message(CHAT_HISTORIAL, cliente_info)
            
            # Enviar mensajes de texto
            for msg in mensajes_texto:
                nombre = msg.get('nombre', 'Usuario')
                timestamp = msg.get('timestamp', '')
                bot.send_message(
                    CHAT_HISTORIAL,
                    f"👤 {nombre} ({timestamp}):\n{msg['content']}"
                )
            
            # Si hay imágenes, enviar un mensaje indicando que vienen las imágenes
            if imagenes:
                bot.send_message(CHAT_HISTORIAL, "\n📸 Imágenes de la conversación:")
                
                # Enviar cada imagen con su información
                for msg in imagenes:
                    nombre = msg.get('nombre', 'Usuario')
                    timestamp = msg.get('timestamp', '')
                    try:
                        bot.send_photo(
                            CHAT_HISTORIAL,
                            msg.get('file_id'),
                            caption=f"📸 Imagen de {nombre} ({timestamp})"
                        )
                    except Exception as e:
                        print(f"Error al enviar imagen: {e}")
                        bot.send_message(
                            CHAT_HISTORIAL,
                            f"❌ Error al enviar imagen de {nombre} ({timestamp})"
                        )
            
        except Exception as e:
            print(f"Error al enviar historial: {e}")

    # Notificar a ambas partes
    try:
        if tipo == "operador":
            # Crear markup para calificación
            markup = types.InlineKeyboardMarkup(row_width=5)
            markup.add(
                types.InlineKeyboardButton("⭐", callback_data=f"calificar_{chat_id}_1"),
                types.InlineKeyboardButton("⭐", callback_data=f"calificar_{chat_id}_2"),
                types.InlineKeyboardButton("⭐", callback_data=f"calificar_{chat_id}_3"),
                types.InlineKeyboardButton("⭐", callback_data=f"calificar_{chat_id}_4"),
                types.InlineKeyboardButton("⭐", callback_data=f"calificar_{chat_id}_5")
            )
            
            bot.send_message(chat_id, 
                "✅ El operador ha cerrado el chat\n\n"
                "Por favor, califica la atención recibida:",
                reply_markup=markup
            )
        elif tipo == "cliente":
            bot.send_message(chat_id, "✅ Has cerrado el chat")
    except Exception as e:
        print(f"Error al enviar mensajes de cierre: {e}")

    # Limpiar datos
    del conversaciones_activas[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('calificar_'))
def procesar_calificacion(call):
    try:
        _, chat_id, calificacion = call.data.split('_')
        calificacion = int(calificacion)
        
        # Aquí podrías guardar la calificación en una base de datos
        # Por ahora solo mostraremos un mensaje
        bot.edit_message_text(
            f"⭐ Gracias por tu calificación: {'⭐' * calificacion}\n"
            "¡Tu opinión es importante para mejorar nuestro servicio!",
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
        
        bot.answer_callback_query(call.id, "✅ Calificación registrada")
        
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error al procesar la calificación")
        print(f"Error en procesar_calificacion: {e}")

@bot.message_handler(commands=['uno'])
def uno(message):
    """Comando para elegir un ganador aleatorio de la lista de ganadores"""
    if message.chat.id == ADMIN_CHAT_ID:
        try:
            # Cargar lista de ganadores
            ganadores = cargar_datos(ganadores_collection, 'ganadores')
            
            if not ganadores:
                bot.send_message(message.chat.id, "❌ No hay ganadores en la lista.")
                return
            
            # Elegir ganador aleatorio
            ganador = random.choice(ganadores)
            
            # Crear markup para confirmar o cancelar
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ Confirmar", callback_data=f"confirmar_ganador_{ganador['nombre']}"),
                types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_ganador")
            )
            
            # Mostrar ganador seleccionado
            bot.send_message(
                message.chat.id,
                f"🎯 Ganador seleccionado aleatoriamente:\n\n"
                f"👤 Nombre: {ganador['nombre']}\n"
                f"📱 Celular: {ganador['celular']}\n"
                f"📅 Fecha: {ganador['fecha']}\n"
                f"🎫 Tipo: {ganador['tipo']}\n\n"
                "¿Desea confirmar este ganador?",
                reply_markup=markup
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error al seleccionar ganador: {str(e)}")
    else:
        bot.send_message(message.chat.id, "❌ No tienes permisos para usar este comando.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('confirmar_ganador_', 'cancelar_ganador')))
def procesar_seleccion_ganador(call):
    """Procesa la confirmación o cancelación de la selección de ganador"""
    try:
        if call.data == "cancelar_ganador":
            bot.edit_message_text(
                "❌ Selección de ganador cancelada.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "❌ Selección cancelada")
            return
        
        # Obtener nombre del ganador del callback_data
        nombre_ganador = call.data.replace('confirmar_ganador_', '')
        
        # Cargar lista de ganadores
        ganadores = cargar_datos(ganadores_collection, 'ganadores')
        
        # Encontrar el ganador seleccionado
        ganador = next((g for g in ganadores if g['nombre'] == nombre_ganador), None)
        
        if ganador:
            # Actualizar el mensaje con la confirmación
            bot.edit_message_text(
                f"✅ Ganador confirmado:\n\n"
                f"👤 Nombre: {ganador['nombre']}\n"
                f"📱 Celular: {ganador['celular']}\n"
                f"📅 Fecha: {ganador['fecha']}\n"
                f"🎫 Tipo: {ganador['tipo']}\n\n"
                "🎉 ¡El ganador ha sido registrado!",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
            
            # Notificar al ganador si tiene chat_id
            if 'chat_id' in ganador:
                try:
                    bot.send_message(
                        ganador['chat_id'],
                        f"🎉 ¡Felicitaciones! Has sido seleccionado como ganador.\n\n"
                        f"👤 Nombre: {ganador['nombre']}\n"
                        f"📱 Celular: {ganador['celular']}\n\n"
                        "Nos pondremos en contacto contigo pronto para coordinar la entrega de tu premio. 🏆"
                    )
                except Exception as e:
                    print(f"Error al notificar al ganador: {e}")
            
            bot.answer_callback_query(call.id, "✅ Ganador confirmado")
        else:
            bot.edit_message_text(
                "❌ Error: No se encontró el ganador seleccionado.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "❌ Error al confirmar ganador")
            
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error al procesar la selección: {str(e)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
        bot.answer_callback_query(call.id, "❌ Error al procesar selección")

def iniciar_bot_con_reintentos():
    retries = 0
    while retries < MAX_RETRIES:
        try:
            print(f"Intento {retries + 1} de {MAX_RETRIES} para iniciar el bot...")
            bot.polling(none_stop=True, timeout=60)
            break
        except Exception as e:
            retries += 1
            print(f"Error al iniciar el bot: {e}")
            if retries < MAX_RETRIES:
                print(f"Reintentando en {RETRY_DELAY} segundos...")
                time.sleep(RETRY_DELAY)
            else:
                print("Se alcanzó el número máximo de reintentos. Saliendo...")
                raise

# Inicializar MongoDB
inicializar_mongodb()

# Iniciar el bot
if __name__ == '__main__':
    print('Iniciando bot...')
    
    # Verificar conexión a MongoDB
    try:
        client.admin.command('ping')
        print("✅ Conexión exitosa a MongoDB!")
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")
        exit(1)
    
    # Iniciar el bot con reintentos
    try:
        iniciar_bot_con_reintentos()
    except Exception as e:
        print(f"❌ Error fatal al iniciar el bot: {e}")
        exit(1)
    