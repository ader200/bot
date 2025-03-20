from telebot import TeleBot
from telethon import TelegramClient, events
from datetime import datetime
import random
import json
from PIL import Image
from io import BytesIO
import qrcode
import telebot
import os
import shutil
import time
import uuid

# Definir el ID de API y el hash aquí
api_id = '23624450'
api_hash = '7aaea69f49653723beb831a46b87db44'
# Aquí también puedes definir el nombre corto de la aplicación
nombre_app = '@SuerteGarantizada_bot'
ad = '6824080362:AAH9YKYT0xTLPnc0Z597YjVLXNCo4nvgl-8'
now = datetime.now()
current_time = now.strftime("%H:%M:%S")



bot = TeleBot(ad)




def verificar_limite_numeros():
    # Cargar el límite de números desde el archivo limite_numeros.json
    with open("limite_numeros.json", "r") as file:
        limite_numeros = json.load(file)
    
    # Verificar si el límite superior ha sido alcanzado
    if limite_numeros["limite_superior"] > 0:
        return True
    else:
        return False

def generar_numero_unico():
    # Verificar el límite de números
    if verificar_limite_numeros():
        # Generar un número único
        return str(uuid.uuid4())
    else:
        return None

def obtener_nombre_imagen(chat_id, extension):
    # Definir las carpetas donde se guardarán las imágenes
    carpetas_imagenes = ["imagenes", "imagenes1", "imagenes2", 'borradores', 'guardados','archivos rifas']
    cd = 'imagenes'
    # Buscar el último número asignado al chat_id en ambas carpetas
    for carpeta in carpetas_imagenes:
        archivos = [filename for filename in os.listdir(carpeta) if filename.startswith(str(chat_id)) and filename.endswith(extension)]
        if archivos:
            secuencia_numeros = [int(filename.split(str(chat_id))[-1][1:-len(extension)]) for filename in archivos]
            siguiente_numero = max(secuencia_numeros) + 1
            break
    else:
        siguiente_numero = 1

    # Construir el nombre de archivo único
    return f"{cd}/{chat_id}a{siguiente_numero}{extension}"






def guardar_datos_compra(numero_unico, nombre, celular, chat_id, nombre_imagen):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos_compra = {
        "numero_unico": numero_unico,
        "nombre": nombre,
        "numero": celular,
        "chat_id": chat_id,
        "nombre_imagen": os.path.basename(nombre_imagen),  # Incluir el nombre de la imagen
        "fecha_registro": fecha_actual
    }

    # Función para cargar datos existentes de un archivo JSON
    def cargar_datos_json(nombre_archivo):
        if os.path.exists(nombre_archivo):
            with open(nombre_archivo, "r") as file:
                try:
                    datos = json.load(file)
                    if isinstance(datos, list):
                        return datos
                except json.JSONDecodeError:
                    pass
        return []

    # Función para guardar datos en un archivo JSON
    def guardar_datos_json(nombre_archivo, datos):
        with open(nombre_archivo, "w") as file:
            json.dump(datos, file, indent=4)
    
    # Cargar datos existentes de los archivos JSON
    datos_numeros_generados = cargar_datos_json("numeros_generados.json")
    datos_imagenes2 = cargar_datos_json("imagenes2.json")
    datos_imagenes3 = cargar_datos_json("imagenes3.json")
    
    # Agregar los nuevos datos de compra a las listas
    datos_numeros_generados.append(datos_compra)
    datos_imagenes2.append(datos_compra)
    datos_imagenes3.append(datos_compra)
    
    # Guardar los datos actualizados en los archivos JSON
    guardar_datos_json("numeros_generados.json", datos_numeros_generados)
    guardar_datos_json("imagenes2.json", datos_imagenes2)
    guardar_datos_json("imagenes3.json", datos_imagenes3)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    cc = message



    bot.reply_to(cc, "¡Bienvenido a la plataforma de rifas y sorteos!\n\n" \
            "Somos una plataforma a nivel nacional de rifas y sorteos en Ecuador\n\nAquí te contamos cómo puedes participar:\n\n" \
            "1. **¿Cómo participar?**\n" \
            "   - Ingresa el comando /comprar_rifa\n" \
            "   - Ingresa tu nombre\n" \
            "   - Proporciona tu número de teléfono\n" \
            "   - Adjunta una foto del comprobante de pago de tu rifa.\n" \
            "   - Recuerda, el costo de la rifa es de un dólar y solo aceptamos transferencias bancarias desde el Banco de Pichincha para tu seguridad.\n\n" \
            "2. **¿Por qué elegirnos?**\n\n" \
            "   - **Ganancias acumuladas:**\nTodos los participantes tienen la oportunidad de ganar el acumulado de todas las entradas vendidas.\n\n" \
            "   - **Números únicos:**\nAsignamos números únicos de manera aleatoria a cada participante, eliminando cualquier posibilidad de manipulación.\n\n" \
            "   - **Seguridad garantizada:**\nNuestro sistema opera fuera de internet, asegurando la protección contra posibles ataques cibernéticos.\n\n" \
            "   - **Beneficios exclusivos:**\nOfrecemos beneficios tanto para los participantes regulares como para aquellos que han sido ganadores en el pasado.\n\n" \
            "3. **¿Qué esperar?**\n" \
            "   Una vez enviado tu comprobante, espera un momento mientras verificamos la información. En caso de que necesitemos más información, nos pondremos en contacto contigo.\n\n" \
            "¡Comencemos! ¿En qué podemos ayudarte hoy?\n\n" \
            "Opciones disponibles:\n\n" \
            "/comprar_rifa - Comprar una rifa por un dólar.\n\n" \

            "Visita nuestra página web para más información:\n\n /pagina_web\n\n"
            '/facebook: Conéctate con nosotros en Facebook para estar al día. 👍\n\n'  

            )

    with open('F:/programa de rifas comleto y para hacer mejoras/th.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

    bot.reply_to(cc,"/comprar_rifa: ¡Participa en nuestra rifa por solo un dólar! ¡Grandes premios te esperan!.🎉\n\n"\
 
                    "/help - Mostrar ayuda\n\n"\
                    "^^^^^^^ Para una información más detallada, le recomendamos revisar el texto anterior, ^^^^^^^ donde se encuentra todo el contenido relevante. ^^^^^^^"
                 )
                 


@bot.message_handler(commands=['help'])
def handle_help_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "¡Claro! Aquí tienes una lista de comandos disponibles:")
    bot.send_message(chat_id, "/start - Iniciar la conversación")
    bot.send_message(chat_id, "/comprar_rifa: ¡Participa en nuestra rifa por solo un dólar! ¡Grandes premios te esperan!.🎉\n\n")



@bot.message_handler(commands=['verificar_rifa'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'hola'
    bot.send_message(chat_id, respuesta)





@bot.message_handler(commands=['facebook'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'https://www.facebook.com/profile.php?id=100077054252925'
    bot.send_message(chat_id, respuesta)

@bot.message_handler(commands=['pagina_web'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = ' https://suertegarantizadaorifasinmanipulacion.durablesites.com?pt=NjY0NGM0N2I5ZjFkMmZkYjhlMTMzMTNmOjE3MTU5OTcyOTguMzAxOnByZXZpZXc='
    bot.send_message(chat_id, respuesta)

@bot.message_handler(commands=['hora'])
def handle_hora_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, current_time)


@bot.message_handler(commands=['comprar_rifa'])
def comprar_rifa(message):
    cid = message.chat.id
    bot.send_message(cid, "¡Hola! Por favor, dime tu nombre completo (nombre y apellido):")
    bot.register_next_step_handler(message, pedir_nombre)

def pedir_nombre(message):
    cid = message.chat.id
    nombre = message.text.strip()
    
    # Verificar si el nombre contiene dos palabras (nombre y apellido)
    if len(nombre.split()) == 2 and all(word.isalpha() for word in nombre.split()):
        bot.send_message(cid, f"Gracias, {nombre}. Ahora, por favor, dime tu número de celular:")
        bot.register_next_step_handler(message, pedir_celular, nombre)  # Pasar el nombre como argumento adicional
    else:
        bot.send_message(cid, "Por favor, ingresa tu nombre completo (nombre y apellido).")
        bot.register_next_step_handler(message, pedir_nombre)

def pedir_celular(message, nombre):  # Agregar el parámetro 'nombre' aquí
    cid = message.chat.id
    celular = message.text.strip()
    
    # Verificar si el número de celular contiene solo números
    if celular.isdigit():
        bot.send_message(cid, 
     f"Perfecto, tu número de celular es:\n\n{celular}.\n\n" \
    "Por favor, proceda a depositar el monto correspondiente al número de boletos que desea adquirir:\n\n" \
    "**Banco Pichincha**\n" \
    "Cuenta de ahorro transaccional\n" \
    "Número: /2209547823\n\n" \
    "Sugerencia: Mantén presionado el número de cuenta para copiarlo fácilmente y no te olvides de borrar el (/).\n\n" \
    "Ahora, envíame una foto del comprobante de pago.\n\n" \
    "¡Gracias por su preferencia y apoyo!")
        
        bot.register_next_step_handler(message, procesar_comprobante, nombre, celular)  # Pasar el nombre y celular como argumentos adicionales
    else:
        bot.send_message(cid, "Por favor, ingresa solo números para el número de celular.")
        bot.register_next_step_handler(message, pedir_celular, nombre)  # Pasar el nombre como argumento adicional

def procesar_comprobante(message, nombre, celular):
    cid = message.chat.id
    if message.photo:
        file_id = message.photo[-1].file_id
        bot.send_message(cid, 
    "¡Gracias! Hemos recibido tu comprobante de pago y está siendo procesado para su verificación. Por favor, espera un momento.\n\n" \
    "Si deseas, puedes comprar otro boleto mientras se verifica tu comprobante. Si no recibes ningún mensaje en un lapso de 24 horas, significa que tu comprobante es falso y no recibirás ningún mensaje de vuelta.\n\n "\
    f'\n\n\n\nCódigo de contacto:\n\n/{cid}'\
    )

        # Generar un número único
        numero_unico = generar_numero_unico()

        if numero_unico:
            # Guardar el nombre de la imagen
            extension = ".jpg"
            nombre_imagen = obtener_nombre_imagen(cid, extension)

            # Guardar los datos de la compra
            guardar_datos_compra(numero_unico, nombre, celular, cid, nombre_imagen)

            # Guardar la imagen del comprobante
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(nombre_imagen, 'wb') as new_file:
                new_file.write(downloaded_file)
        else:
            bot.send_message(cid, "Lo siento, el límite de números ha sido alcanzado.")
    else:
        bot.send_message(cid, "Por favor, envía una foto del comprobante de pago.")
        bot.register_next_step_handler(message, procesar_comprobante, nombre, celular)

@bot.message_handler(content_types=['text'])
def bot_mensajes_texto(message):


  if message.text.startswith('/'):
    bot.send_message(message.chat.id, 'comando no disponible')
  else:
    bot.send_message(message.chat.id, '/start Aqui hay toda la informacion. ')
    bot.send_message(message.chat.id, "/comprar_rifa - Comprar una rifa por un dólar.\n\n")


bot.polling()
print('iniciando')