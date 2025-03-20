import os
import json
import time

def limpiar_nombre(nombre):
    # Eliminar números y paréntesis del nombre de archivo
    nombre_limpio = nombre.replace(" (2).png", "").replace(" (1).png", "").replace(".png", "")
    return nombre_limpio

def main():
    # Ruta de la carpeta qr
    carpeta_qr = "./qr"

    # Lista para almacenar los nombres de las imágenes limpios
    nombres_imagenes = []

    # Recorrer los archivos en la carpeta qr
    for filename in os.listdir(carpeta_qr):
        # Verificar que sea un archivo png
        if filename.endswith(".png"):
            # Obtener el nombre original de la imagen
            nombre_original = filename.replace(".png", "")
            # Obtener el nombre limpio de la imagen
            nombre_limpio = limpiar_nombre(filename)
            # Agregar el nombre original y el nombre limpio a la lista
            nombres_imagenes.append({"chat_id": nombre_limpio, "imagen": filename})

    # Guardar los nombres de las imágenes en qr.json
    with open("qr.json", "w") as file:
        json.dump(nombres_imagenes, file, indent=2)

# Bucle principal
while True:
    main()
    # Esperar 5 segundos antes de volver a ejecutar
    time.sleep(5)
