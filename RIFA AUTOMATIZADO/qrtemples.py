from telebot import TeleBot
import os
import json
import telebot
from datetime import datetime


# Token del bot

ad = '7102547547:AAG_bVxacn4f8KjEjN-oUyMLmaznI_PSv1A'


bot = TeleBot(ad)

bot = telebot.TeleBot(ad)

def enviar_mensaje_con_datos():
    try:
        # Abrir y cargar el archivo JSON de qr
        with open('qr.json') as qr_file:
            qr_data = json.load(qr_file)

        mensajes_enviados = []

        # Verificar si se leyeron datos del archivo JSON de qr
        if qr_data:
            # Iterar sobre los datos de qr
            for qr_entry in qr_data:
                chat_id = str(qr_entry['chat_id'])  # Asegurarse de que el chat_id sea una cadena
                imagen = qr_entry['imagen']

                # Enviar mensaje con la imagen
                mensaje = "Hola, aquí tienes tu QR:"
                try:
                    bot.send_message(chat_id, mensaje)
                    with open(f'qr/{imagen}', 'rb') as image_file:
                        bot.send_photo(chat_id, image_file)
                    mensajes_enviados.append(chat_id)
                except telebot.apihelper.ApiException as e:
                    print(f"Error al enviar mensaje a {chat_id}: {e}")

            # Si se enviaron mensajes, mover archivos
            if mensajes_enviados:
                mover_archivos('qr', 'qr1')

        # Abrir y cargar el archivo JSON de lista
        with open('lista.json') as lista_file:
            lista_data = json.load(lista_file)

        # Verificar si se leyeron datos del archivo JSON de lista
        if lista_data:
            lista1_data = []
            # Iterar sobre los datos de lista y actualizar la información
            for lista_entry in lista_data:
                chat_id = str(lista_entry['chat_id'])  # Asegurarse de que el chat_id sea una cadena

                # Buscar la entrada correspondiente en qr_data
                qr_entry = next((entry for entry in qr_data if str(entry['chat_id']) == chat_id), None)

                # Si se encuentra la entrada en qr_data, actualizar la información
                if qr_entry and chat_id in mensajes_enviados:
                    nombre = lista_entry['nombre']
                    cuenta_de_banco = lista_entry['cuenta_de_banco']
                    nueva_imagen = qr_entry['imagen']

                    # Agregar la información actualizada a la lista1_data
                    lista1_data.append({
                        'nombre': nombre,
                        'cuenta_de_banco': cuenta_de_banco,
                        'chat_id': chat_id,
                        'imagen': nueva_imagen
                    })

            # Guardar la información actualizada en lista1.json
            with open('lista1.json', 'w') as lista1_file:
                json.dump(lista1_data, lista1_file, indent=4)

    except Exception as e:
        print("Error al enviar mensajes:", e)

def mover_archivos(origen, destino):
    if not os.path.exists(destino):
        os.makedirs(destino)
    archivos = os.listdir(origen)
    for index, archivo in enumerate(archivos):
        nuevo_nombre = f"archivo_{index+1}.png"  # Cambiar el formato del nombre como desees
        destino_final = os.path.join(destino, nuevo_nombre)
        # Verificar si el archivo destino ya existe y ajustar el nombre si es necesario
        contador = 1
        while os.path.exists(destino_final):
            nuevo_nombre = f"archivo_{index+1}_{contador}.png"
            destino_final = os.path.join(destino, nuevo_nombre)
            contador += 1
        os.rename(os.path.join(origen, archivo), destino_final)

# Llamar a la función principal
enviar_mensaje_con_datos()
