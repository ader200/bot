import os
import json
import qrcode
from telebot import TeleBot

# Token del bot
ad = '6824080362:AAH9YKYT0xTLPnc0Z597YjVLXNCo4nvgl-8'

bot = TeleBot(ad)

# Función para enviar mensaje con datos del JSON
def enviar_mensaje_con_datos():
    try:
        # Abrir y cargar el archivo JSON
        with open('imagenes1.json') as json_file:
            datos = json.loads(json_file.read())
        
        # Verificar si se leyeron datos del JSON
        if datos:
            # Agrupar los datos por nombre y numero
            datos_agrupados = {}
            for dato in datos:
                nombre = dato['nombre']
                numero = dato['numero']
                chat_id = dato['chat_id']
                
                clave = (nombre, numero, chat_id)
                if clave not in datos_agrupados:
                    datos_agrupados[clave] = {
                        'numero_unico': [],
                        'nombre': nombre,
                        'numero': numero,
                        'chat_id': chat_id
                    }
                datos_agrupados[clave]['numero_unico'].append(dato['numero_unico'])
            
            # Iterar sobre los datos agrupados y enviar mensajes
            for clave, datos in datos_agrupados.items():
                numeros_unicos = "\n".join(datos['numero_unico'])
                nombre = datos['nombre']
                numero = datos['numero']
                chat_id = datos['chat_id']
                
                # Generar QR
                qr_data = f"Números Únicos:\n{numeros_unicos}\nNombre: {nombre}\nNúmero: {numero}"
                qr_filename = f"{nombre}_{numero}.png"
                generar_qr(qr_data, qr_filename)
                
                # Enviar mensaje con QR
                mensaje = f"Hola {nombre}, aquí tienes tu QR con los siguientes datos:\nNúmeros Únicos:\n{numeros_unicos}\nNombre: {nombre}\nNúmero: {numero}"
                bot.send_message(chat_id, mensaje)
                with open(qr_filename, 'rb') as qr_file:
                    bot.send_photo(chat_id, qr_file)
                os.remove(qr_filename)  # Eliminar QR después de enviarlo
                
                # Mover archivos a carpeta imagenes2
                mover_archivos('imagenes1', 'imagenes2')
                
                # Mensaje de despedida
                despedida = ("Gracias por tu espera. Tu comprobante de pago ha sido verificado. "
                             "¡Recuerda que en nuestra plataforma ofrecemos la oportunidad de ganar premios emocionantes "
                             "por tan solo un dólar! Participa nuevamente para aumentar tus chances de ganar. "
                             "¡Buena suerte y hasta pronto!")
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
    img = qr.make_image(fill_color="black", back_color="white")
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
