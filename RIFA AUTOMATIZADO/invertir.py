from telebot import TeleBot
import random
import os
import json
from datetime import datetime

ad = '7122980249:AAFuaLBLjyOYAmwL0NR3C7C8kc9uCLiuYkQ'

bot = TeleBot(ad)




# Asegúrate de que la carpeta 'inversion' existe
for folder in ['inversion', 'inversion1', 'inversion2', 'borradores1']:
    if not os.path.exists(folder):
        os.makedirs(folder)
        
# Archivo JSON para guardar las inversiones
inversiones_file = 'invertir.json'

# Número máximo de intentos
MAX_INTENTOS = 2

# Diccionario para almacenar los intentos de cada usuario
user_attempts = {}


@bot.message_handler(commands=['start'])
def start(message):

    with open('F:/programa de rifas comleto y para hacer mejoras/3.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

    bot.send_message(message.chat.id, 
                 "¡Bienvenido al Bot de Inversiones! 😊\n\n"
                 "Para comenzar, utiliza el comando.\n\n/invertir\n\n Sigue las instrucciones para proporcionar la siguiente información:\n\n"
                 "1. Tu nombre\n"
                 "2. Número de cuenta\n"
                 "3. Cantidad a invertir\n"
                 "4. Comprobante de pago\n\n"
                 "¡Te deseamos mucho éxito en tus inversiones! 📈💼")

@bot.message_handler(commands=['Soporte'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'https://www.facebook.com/permalink.php?story_fbid=453345640577241&id=100077054252925&ref=embed_post'
    bot.send_message(chat_id, respuesta)

# Comando para iniciar el proceso de inversión
@bot.message_handler(commands=['invertir'])
def invertir(message):
    cid = message.chat.id
    user_attempts[cid] = {'nombre': 0, 'celular': 0, 'inversion': 0, 'comprobante': 0}
    bot.send_message(cid, "¡Hola! Por favor, dime tu nombre completo (nombre y apellido):")
    bot.register_next_step_handler(message, pedir_nombre)

def pedir_nombre(message):
    nombre = message.text
    cid = message.chat.id
    user_attempts[cid]['nombre'] += 1
    if len(nombre.split()) == 2:
        bot.send_message(cid, f"Gracias, {nombre}. Por favor, dime tu número de cuenta Ejemplo:  Produbanco\n\nPINTO RODRIGUEZ PEPE PAUL  \nC\u00e9dula: 1725464654\nCta Ahorro Produbanco\nN\u00famero:\u00a014569864651\n\nPichincha:\n\n Cta Ahorro Pichincha\n\nN\u00famero:\u00a0175698454651. ")
        bot.register_next_step_handler(message, pedir_celular, nombre)
    else:
        if user_attempts[cid]['nombre'] < MAX_INTENTOS:
            bot.send_message(cid, "Por favor, ingresa tu nombre completo (nombre y apellido):")
            bot.register_next_step_handler(message, pedir_nombre)
        else:
            bot.send_message(cid, "Has excedido el número de intentos. Por favor, inicia de nuevo con /invertir.")
            user_attempts[cid] = {'nombre': 0, 'celular': 0, 'inversion': 0, 'comprobante': 0}

def pedir_celular(message, nombre):
    celular = message.text
    cid = message.chat.id
    user_attempts[cid]['celular'] += 1
    bot.send_message(cid, f"Perfecto, {nombre}. ¿Cuánto dinero deseas invertir?")
    bot.register_next_step_handler(message, pedir_inversion, nombre, celular)

def pedir_inversion(message, nombre, celular):
    try:
        inversion = float(message.text)
        cid = message.chat.id
        bot.send_message(cid, f"Gracias, {nombre}.\n\n" \
    f"Por favor, proceda a depositar el monto correspondiente que es {inversion}:\n\n" \
    "**Banco Pichincha**\n" \
    "Cuenta de ahorro transaccional\n" \
    "Número: /2209547823\n\n" \
    "Sugerencia: Mantén presionado el número de cuenta para copiarlo fácilmente y no te olvides de borrar el (/).\n\n" \
    "Ahora, envíame una foto del comprobante de pago.\n\n" \
    "¡Gracias por su preferencia y apoyo!")   
            
        bot.register_next_step_handler(message, pedir_comprobante, nombre, celular, inversion)
    except ValueError:
        cid = message.chat.id
        user_attempts[cid]['inversion'] += 1
        if user_attempts[cid]['inversion'] < MAX_INTENTOS:
            bot.send_message(cid, "Por favor, introduce una cantidad válida de dinero.")
            bot.register_next_step_handler(message, pedir_inversion, nombre, celular)
        else:
            bot.send_message(cid, "Has excedido el número de intentos. Por favor, inicia de nuevo con /invertir.")
            user_attempts[cid] = {'nombre': 0, 'celular': 0, 'inversion': 0, 'comprobante': 0}

def pedir_comprobante(message, nombre, celular, inversion):
    cid = message.chat.id
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        folder = random.choice(['inversion', 'inversion1', 'inversion2'])
        fo = 'inversion'
        imagen_filename = f"{nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        full_path = os.path.join(fo, imagen_filename)

        with open(full_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        posible_ganancia = calcular_ganancia(inversion)

        guardar_inversion(nombre, celular, inversion, posible_ganancia, imagen_filename, cid)

        bot.send_message(cid, f"Dependiendo de la participación, podrías ganar entre ${inversion * 1.01:.2f} y ${inversion * 1.25:.2f}.")
        bot.send_message(cid, 
    "¡Gracias! Hemos recibido tu comprobante de pago y está siendo procesado para su verificación. Por favor, espera un momento.\n\n" \
    "Si no recibes ningún mensaje en un lapso de 3 días, significa que tu comprobante es falso y no recibirás ningún mensaje de vuelta.\n\n "\
    f' Soporte: Envíanos tus Recomendaciones y Errores 🚀\n\nCódigo de contacto:\n\n/{cid}\n\n'\
    f'visite nuestra página de Facebook:\n\n/Soporte'
                        )
    else:
        user_attempts[cid]['comprobante'] += 1
        if user_attempts[cid]['comprobante'] < MAX_INTENTOS:
            bot.send_message(message.chat.id, "Por favor, envía una foto válida del comprobante de pago.")
            bot.register_next_step_handler(message, pedir_comprobante, nombre, celular, inversion)
        else:
            bot.send_message(cid, "Has excedido el número de intentos. Por favor, inicia de nuevo con /invertir.")
            user_attempts[cid] = {'nombre': 0, 'celular': 0, 'inversion': 0, 'comprobante': 0}

def guardar_inversion(nombre, celular, inversion, ganancia_calculada, imagen_filename, chat_id):
    inversion_data = {
        "nombre": nombre,
        "celular": celular,
        "inversion": inversion,
        "ganancia_calculada": ganancia_calculada,
        "imagen": imagen_filename,
        "chat_id": chat_id,
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if os.path.exists(inversiones_file) and os.path.getsize(inversiones_file) > 0:
        with open(inversiones_file, 'r') as f:
            try:
                inversiones = json.load(f)
            except json.JSONDecodeError:
                inversiones = []
    else:
        inversiones = []

    inversiones.append(inversion_data)

    with open(inversiones_file, 'w') as f:
        json.dump(inversiones, f, indent=4)

def calcular_ganancia(inversion):
    ganancia_porcentaje = random.uniform(1.01, 1.25)
    return inversion * ganancia_porcentaje

@bot.message_handler(content_types=['text'])
def bot_mensajes_texto(message):


  if message.text.startswith('/'):
    bot.send_message(message.chat.id, 'comando no disponible')
  else:
    bot.send_message(message.chat.id, '/start Aqui hay toda la informacion. ')
    bot.send_message(message.chat.id, 'Utiliza el comando: /invertir. ')



# Iniciar el bot
bot.polling()

