import os
import json
import time
import re

def limpiar_nombre(nombre):
    # Eliminar números y paréntesis del nombre de archivo
    nombre_limpio = nombre.replace(" (2).png", "").replace(" (1).png", "").replace(".png", "")
    return nombre_limpio

def main():
    # Ruta de la carpeta qr
    carpeta_qr = r"F:\descargas"

    json_path = "mt.json"

    if os.path.exists(json_path):
        with open(json_path, "r") as file:
            try:
                nombres_imagenes = json.load(file)
            except json.JSONDecodeError:
                nombres_imagenes = []

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

    # Guardar los nombres de las imágenes en mt.json
    with open("mt.json", "w") as file:
        json.dump(nombres_imagenes, file, indent=2)


while True:
    main()
    # Esperar 5 segundos antes de volver a ejecutar
    time.sleep(5)
