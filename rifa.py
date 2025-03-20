import os
import json
import qrcode
import uuid
from telebot import TeleBot, types
from datetime import datetime
import random

# Token del bot
TOKEN = '6824080362:AAH9YKYT0xTLPnc0Z597YjVLXNCo4nvgl-8'
ADMIN_CHAT_ID = 5498545183

# Inicializar el bot
bot = TeleBot(TOKEN)

# Archivos JSON
REGISTRO_FILE = 'registro.json'
COMPRAS_FILE = 'compras.json'
GANADORES_FILE = 'ganadores.json'
GRATIS_FILE = 'gratis.json'
CODIGOS_FILE = 'codigos.json'

# Asegurarse de que los archivos JSON existan
def inicializar_json():
    archivos = [REGISTRO_FILE, COMPRAS_FILE, GANADORES_FILE, GRATIS_FILE, CODIGOS_FILE]
    for archivo in archivos:
        if not os.path.exists(archivo):
            with open(archivo, 'w') as f:
                json.dump({}, f)

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

# Cargar datos JSON
def cargar_json(archivo):
    try:
        with open(archivo, 'r') as f:
            return json.load(f)
    except:
        return {}

# Guardar datos JSON
def guardar_json(archivo, datos):
    with open(archivo, 'w') as f:
        json.dump(datos, f, indent=4)

# Comando /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "¡Bienvenido al Bot de Rifas! 🎉\n\n"
                         "Comandos disponibles:\n"
                         "/rifa - Comprar rifa\n"
                         "/gratis - Obtener rifa gratis\n"
                         "/ganador - Elegir ganador (solo admin)\n"
                         "/ganadorz - Gestionar lista de ganadores (solo admin)\n"
                         "/uno - Elegir ganador aleatorio (solo admin)\n"
                         "/pi - Elegir ganador gratis (solo admin)")

# Comando /rifa
@bot.message_handler(commands=['rifa'])
def rifa(message):
    chat_id = message.chat.id
    registro = cargar_json(REGISTRO_FILE)
    
    # Verificar si el usuario ya está registrado
    usuario_existente = next((u for u in registro if u['chat_id'] == chat_id), None)
    
    if usuario_existente:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(usuario_existente['nombre'], "Otro")
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
        registro = cargar_json(REGISTRO_FILE)
        usuario = next((u for u in registro if u['nombre'] == message.text), None)
        if usuario:
            # Auto-rellenar celular y continuar con el proceso
            chat_id = message.chat.id
            
            # Enviar instrucciones de pago
            bot.send_message(chat_id, 
                f"Perfecto, {usuario['nombre']}.\n\n"
                "Por favor, proceda a depositar el monto correspondiente al número de boletos que desea adquirir:\n\n"
                "**Banco Pichincha**\n"
                "Cuenta de ahorro transaccional\n"
                "Número: 2209547823\n\n"
                "Ahora, envíame una foto del comprobante de pago.\n\n"
                "¡Gracias por su preferencia y apoyo!")
            
            bot.register_next_step_handler(message, procesar_comprobante_rifa, usuario['nombre'], usuario['celular'])
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
        registro = cargar_json(REGISTRO_FILE)
        registro.append({
            'nombre': nombre,
            'celular': celular,
            'chat_id': chat_id,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_json(REGISTRO_FILE, registro)
        
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
        
        # Guardar datos temporales
        datos_temp = {
            'nombre': nombre,
            'celular': celular,
            'chat_id': message.chat.id,
            'file_id': message.photo[-1].file_id,
            'comprobante_id': comprobante_id
        }
        
        # Enviar foto con botones al admin
        bot.send_photo(
            ADMIN_CHAT_ID,
            message.photo[-1].file_id,
            caption=f"📝 Verificar comprobante de:\nNombre: {nombre}\nCelular: {celular}\nID: {comprobante_id}",
            reply_markup=markup
        )
        
        # Guardar datos temporales en un diccionario global
        if not hasattr(procesar_comprobante_rifa, 'comprobantes_pendientes'):
            procesar_comprobante_rifa.comprobantes_pendientes = {}
        procesar_comprobante_rifa.comprobantes_pendientes[comprobante_id] = datos_temp
        
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
        
        if comprobante_id in procesar_comprobante_rifa.comprobantes_pendientes:
            datos_temp = procesar_comprobante_rifa.comprobantes_pendientes[comprobante_id]
            
            if decision == 'si':
                bot.send_message(ADMIN_CHAT_ID, "¿Cuántos boletos está comprando?")
                bot.register_next_step_handler(call.message, procesar_cantidad_boletos, datos_temp)
            else:
                bot.send_message(datos_temp['chat_id'], 
                    "Lo sentimos, su comprobante no fue verificado como auténtico. "
                    "Por favor, intente nuevamente con un comprobante válido.")
            
            # Eliminar solo este comprobante específico
            del procesar_comprobante_rifa.comprobantes_pendientes[comprobante_id]
            
            # Actualizar mensaje original
            bot.edit_message_reply_markup(
                chat_id=ADMIN_CHAT_ID,
                message_id=call.message.message_id,
                reply_markup=None
            )
            
            # Mostrar mensaje de cuántos comprobantes quedan pendientes
            pendientes = len(procesar_comprobante_rifa.comprobantes_pendientes)
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
            compras = cargar_json(COMPRAS_FILE)
            compras.append({
                'nombre': datos_temp['nombre'],
                'celular': datos_temp['celular'],
                'chat_id': datos_temp['chat_id'],
                'cantidad': cantidad,
                'numeros_unicos': numeros_unicos,
                'fecha_compra': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            guardar_json(COMPRAS_FILE, compras)
            
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
    bot.send_message(chat_id, 
        "Para obtener una rifa gratis, visita nuestra página web:\n"
        "https://tu-pagina-web-en-render.com\n\n"
        "Copia el código que aparece en la página y envíalo aquí.")
    bot.register_next_step_handler(message, verificar_codigo_gratis)

def verificar_codigo_gratis(message):
    if not message or not message.text:
        return
    if not message.text.startswith('/'):
        chat_id = message.chat.id
        codigo = message.text.strip()
        
        # Verificar código con la página web
        codigos_validos = cargar_json(CODIGOS_FILE)
        if codigo in codigos_validos:
            bot.send_message(chat_id, "¡Código válido! Por favor, ingrese su nombre completo:")
            bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)
        else:
            bot.send_message(chat_id, "Código no válido. Por favor, intente nuevamente.")
            bot.register_next_step_handler(message, verificar_codigo_gratis)

def pedir_nombre_gratis(message, codigo):
    if not message or not message.text:
        return
    nombre = message.text.strip()
    if len(nombre.split()) >= 2:
        bot.send_message(message.chat.id, "Por favor, ingrese su número de celular:")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese su nombre completo (nombre y apellido):")
        bot.register_next_step_handler(message, pedir_nombre_gratis, codigo)

def pedir_celular_gratis(message, nombre, codigo):
    if not message or not message.text:
        return
    celular = message.text.strip()
    if celular.isdigit():
        # Generar número único
        numero_unico = generar_numero_unico()
        
        # Guardar en registro de rifas gratis
        gratis = cargar_json(GRATIS_FILE)
        gratis.append({
            'nombre': nombre,
            'celular': celular,
            'chat_id': message.chat.id,
            'numero_unico': numero_unico,
            'codigo': codigo,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_json(GRATIS_FILE, gratis)
        
        # Generar y enviar QR
        qr_data = f"Número Único: {numero_unico}\nNombre: {nombre}\nCelular: {celular}"
        qr_filename = f"qr_gratis_{message.chat.id}.png"
        generar_qr(qr_data, qr_filename)
        
        with open(qr_filename, 'rb') as qr_file:
            bot.send_photo(message.chat.id, qr_file)
        
        os.remove(qr_filename)
        
        # Mensaje de confirmación
        bot.send_message(message.chat.id,
            f"¡Felicidades, {nombre}! 🎉\n\n"
            "Has obtenido una rifa gratis.\n"
            "Tu número único está en el código QR adjunto.\n\n"
            "¡Buena suerte! 🍀")
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese un número de celular válido:")
        bot.register_next_step_handler(message, pedir_celular_gratis, nombre, codigo)

# Comando /ganador (solo admin)
@bot.message_handler(commands=['ganador'])
def ganador(message):
    if message.chat.id == ADMIN_CHAT_ID:
        compras = cargar_json(COMPRAS_FILE)
        if compras:
            # Elegir ganador aleatorio
            ganador = random.choice(compras)
            bot.send_message(ADMIN_CHAT_ID,
                f"¡Ganador seleccionado!\n\n"
                f"Nombre: {ganador['nombre']}\n"
                f"Celular: {ganador['celular']}\n"
                f"Números: {', '.join(ganador['numeros_unicos'])}")
            
            # Notificar al ganador
            bot.send_message(ganador['chat_id'],
                f"¡Felicidades, {ganador['nombre']}! 🎉\n\n"
                "Has sido seleccionado como ganador.\n"
                "Nos pondremos en contacto contigo pronto.")
        else:
            bot.send_message(ADMIN_CHAT_ID, "No hay compradores registrados.")
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

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
    if not message or not message.text:
        return
    if message.text == "Agregar":
        bot.send_message(message.chat.id, "Ingrese el nombre del ganador:")
        bot.register_next_step_handler(message, agregar_ganador)
    elif message.text == "Eliminar":
        ganadores = cargar_json(GANADORES_FILE)
        if ganadores:
            lista = "\n".join([f"{i+1}. {g['nombre']}" for i, g in enumerate(ganadores)])
            bot.send_message(message.chat.id, f"Seleccione el número del ganador a eliminar:\n\n{lista}")
            bot.register_next_step_handler(message, eliminar_ganador)
        else:
            bot.send_message(message.chat.id, "No hay ganadores registrados.")
    elif message.text == "Ver lista":
        ganadores = cargar_json(GANADORES_FILE)
        if ganadores:
            lista = "\n".join([f"{i+1}. {g['nombre']} - {g['celular']}" for i, g in enumerate(ganadores)])
            bot.send_message(message.chat.id, f"Lista de ganadores:\n\n{lista}")
        else:
            bot.send_message(message.chat.id, "No hay ganadores registrados.")

def agregar_ganador(message):
    if not message or not message.text:
        return
    nombre = message.text.strip()
    bot.send_message(message.chat.id, "Ingrese el número de celular del ganador:")
    bot.register_next_step_handler(message, guardar_ganador, nombre)

def guardar_ganador(message, nombre):
    if not message or not message.text:
        return
    celular = message.text.strip()
    if celular.isdigit():
        ganadores = cargar_json(GANADORES_FILE)
        ganadores.append({
            'nombre': nombre,
            'celular': celular,
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        guardar_json(GANADORES_FILE, ganadores)
        bot.send_message(message.chat.id, "Ganador agregado exitosamente.")
    else:
        bot.send_message(message.chat.id, "Por favor, ingrese un número de celular válido:")

def eliminar_ganador(message):
    if not message or not message.text:
        return
    try:
        indice = int(message.text) - 1
        ganadores = cargar_json(GANADORES_FILE)
        if 0 <= indice < len(ganadores):
            ganador_eliminado = ganadores.pop(indice)
            guardar_json(GANADORES_FILE, ganadores)
            bot.send_message(message.chat.id, f"Ganador '{ganador_eliminado['nombre']}' eliminado exitosamente.")
        else:
            bot.send_message(message.chat.id, "Número de ganador no válido.")
    except ValueError:
        bot.send_message(message.chat.id, "Por favor, ingrese un número válido.")

# Comando /uno (solo admin)
@bot.message_handler(commands=['uno'])
def uno(message):
    if message.chat.id == ADMIN_CHAT_ID:
        ganadores = cargar_json(GANADORES_FILE)
        if ganadores:
            ganador = random.choice(ganadores)
            bot.send_message(ADMIN_CHAT_ID,
                f"¡Ganador seleccionado!\n\n"
                f"Nombre: {ganador['nombre']}\n"
                f"Celular: {ganador['celular']}")
        else:
            bot.send_message(ADMIN_CHAT_ID, "No hay ganadores registrados.")
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

# Comando /pi (solo admin)
@bot.message_handler(commands=['pi'])
def pi(message):
    if message.chat.id == ADMIN_CHAT_ID:
        gratis = cargar_json(GRATIS_FILE)
        if gratis:
            ganador = random.choice(gratis)
            bot.send_message(ADMIN_CHAT_ID,
                f"¡Ganador de rifa gratis seleccionado!\n\n"
                f"Nombre: {ganador['nombre']}\n"
                f"Celular: {ganador['celular']}\n"
                f"Número único: {ganador['numero_unico']}")
            
            # Notificar al ganador
            bot.send_message(ganador['chat_id'],
                f"¡Felicidades, {ganador['nombre']}! 🎉\n\n"
                "Has sido seleccionado como ganador de la rifa gratis.\n"
                "Nos pondremos en contacto contigo pronto.")
        else:
            bot.send_message(ADMIN_CHAT_ID, "No hay participantes en rifas gratis registrados.")
    else:
        bot.send_message(message.chat.id, "No tiene permisos para usar este comando.")

# Inicializar archivos JSON
inicializar_json()

# Iniciar el bot
if __name__ == '__main__':
    print('Iniciando bot...')
    bot.polling() 