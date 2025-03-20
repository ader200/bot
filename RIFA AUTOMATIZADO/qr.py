from telebot import TeleBot
import json
from datetime import datetime
import os


ad = '7102547547:AAG_bVxacn4f8KjEjN-oUyMLmaznI_PSv1A'

bot = TeleBot(ad)

# Inicializar el archivo JSON si no existe o está corrupto
def load_trabajadores():
    try:
        with open('trabajadores.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

trabajadores = load_trabajadores()

@bot.message_handler(commands=['start'])
def start(message):
    response = (
        "¡Bienvenido!\n\n"
        "Aquí encontrarás toda la información sobre cómo ganar dinero con nosotros:\n\n"
        "Por cada visita a los códigos QR de nuestra página web y página de Facebook, recibirás $0.03. "
        "Ambos códigos tienen el mismo valor. Si uno recibe visitas y el otro no, no se pagará. Sin embargo, "
        "si ambos reciben visitas, recibirás $0.03.\n\n"
        "Además, recibirás $0.05 por cada visita directa al enlace del bot, independientemente de los otros dos enlaces.\n\n"
        "Los pagos se realizarán cuando se acabe cada sorteo.\n\n"
        "Para registrarte y obtener tu código QR personalizado, por favor, utiliza el comando /participar."
    )
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['participar'])
def participar(message):
    bot.send_message(message.chat.id, "Por favor, envíame tu nombre y apellido (solo dos palabras). Tienes dos intentos.")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text.strip()
    if len(name.split()) != 2:
        bot.send_message(message.chat.id, "Por favor, envía solo tu nombre y apellido (dos palabras). Último intento.")
        bot.register_next_step_handler(message, get_name_final_attempt)
    else:
        bot.send_message(message.chat.id, "Por favor, solo aceptamos al Banco de Pichincha para mayor seguridad. Dime tu número de cuenta:\nPichincha ejemplo:\n\n Cta Ahorro Pichincha\nN\u00famero:\u00a0175698454651.")
        bot.register_next_step_handler(message, get_bank_account, name)

def get_name_final_attempt(message):
    name = message.text.strip()
    if len(name.split()) != 2:
        bot.send_message(message.chat.id, "Has excedido el número de intentos. Por favor, inicia el registro nuevamente con /participar.")
    else:
        bot.send_message(message.chat.id, "Por favor, solo aceptamos al Banco de Pichincha para mayor seguridad. Dime tu número de cuenta:\nPichincha ejemplo:\n\n Cta Ahorro Pichincha\nN\u00famero:\u00a0175698454651.")
        bot.register_next_step_handler(message, get_bank_account, name)


    

def get_bank_account(message, name):
    bank_account = message.text.strip()
    chat_id = message.chat.id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Guardar los datos en el archivo JSON
    worker_data = {
        'nombre': name,
        'cuenta_de_banco': bank_account,
        'chat_id': chat_id,
        'fecha_y_hora': timestamp


    }
    trabajadores.append(worker_data)
    
    with open('trabajadores.json', 'w') as file:
        json.dump(trabajadores, file, indent=4)

    # Enviar mensaje de despedida
    farewell_message = (
        "Se está verificando sus datos para ver si puede trabajar aquí. "
        "Si en el lapso de 3 días no le llega su QR, es porque usted ya está participando en este trabajo y ya tiene sus QR, "
        "o no fue admitido en este trabajo. Esperamos que entienda, perdón por las molestias."
    )
    bot.send_message(message.chat.id, farewell_message)
@bot.message_handler(content_types=['text'])
def bot_mensajes_texto(message):


  if message.text.startswith('/'):
    bot.send_message(message.chat.id, 'comando no disponible')
  else:
    bot.send_message(message.chat.id, '/start Aqui hay toda la informacion. ')  
    bot.send_message(message.chat.id, 'Utiliza el comando /participar. ')



# No olvides iniciar el bot con bot.polling() al final del script
bot.polling()