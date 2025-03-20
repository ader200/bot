import os
import json
import qrcode
from telebot import TeleBot

# Token del bot
ad = '7122980249:AAFuaLBLjyOYAmwL0NR3C7C8kc9uCLiuYkQ'

bot = TeleBot(ad)

# Función para enviar mensaje con datos del JSON
def enviar_mensaje_con_datos():
    try:
        # Abrir y cargar el archivo JSON
        with open('invertir1.json') as json_file:
            datos = json.loads(json_file.read())
        
        # Verificar si se leyeron datos del JSON
        if datos:
            # Iterar sobre los datos y enviar mensajes
            for dato in datos:  
                nombre = dato['nombre']
                celular = dato['celular']
                inversion = dato['inversion']
                ganancia_calculada = dato['ganancia_calculada']
                imagen= dato['imagen']
                chat_id = dato['chat_id']
               
                # Generar QR
                qr_data = f"inversion: {inversion}\nNombre: {nombre}\nNúmero: {celular}"
                qr_filename = f"{inversion}.png"
                generar_qr(qr_data, qr_filename)
                
                # Enviar mensaje con QR
                mensaje = f"Hola {nombre}, aquí tienes tu QR con los siguientes datos:\nVale: {inversion}\nEs para canjear su dinero si hay un error\nTe veo en la siguiente rifa cuidate"
                bot.send_message(chat_id, mensaje)
                with open(qr_filename, 'rb') as qr_file:
                    bot.send_photo(chat_id, qr_file)
                os.remove(qr_filename)  # Eliminar QR después de enviarlo
                
                # Mover archivos a carpeta imagenes2
                mover_archivos('inversion1', 'inversion2')
                
                # Mensaje de despedida
                despedida = ("Gracias por tu espera. Tu comprobante de pago ha sido verificado.\n "
                             "¡Recuerda que en nuestra plataforma ofrecemos la oportunidad de ganar.\n"
                             "su ganacia se regresa a lo que se acaba la rifa y hay un ganador. Le llegara un mesaje cuando ya este depocitado en su cuenta.\n"
                             " ¡Buena suerte y hasta pronto!")
                bot.send_message(chat_id, despedida)
                
        else:
            print("No se leyeron datos del archivo JSON.")

    except Exception as e:
        print("Error al enviar mensajes:", e)

# Función para generar QR
def generar_qr(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="white", back_color="black")
    img.save(filename)

# Función para mover archivos de una carpeta a otra
def mover_archivos(origen, destino):
    archivos = os.listdir(origen)
    for archivo in archivos:
        os.rename(os.path.join(origen, archivo), os.path.join(destino, archivo))

# Ejemplo de uso de la función
if __name__ == '__main__':
    print('Iniciando envío de mensajes...')
    enviar_mensaje_con_datos()
    print('Mensajes enviados y archivos movidos.')
