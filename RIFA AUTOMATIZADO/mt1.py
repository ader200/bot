import os
import json
import shutil
import time
from collections import defaultdict

# Define las rutas de las carpetas
descargas_path = r"F:\descargas"
destino_path = r"F:\programa de rifas comleto y para hacer mejoras\qr"
json_path = r"F:\programa de rifas comleto y para hacer mejoras\mt.json"
intervalo_verificacion = 20  # Intervalo de verificación en segundos

while True:
    # Lee el archivo JSON para obtener los datos
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Agrupa las imágenes por chat_id
    chat_images = defaultdict(list)
    for entry in data:
        chat_id = entry['chat_id']
        imagen = entry['imagen']
        chat_images[chat_id].append(imagen)

    # Recorre cada chat_id y verifica la existencia de las imágenes
    for chat_id, image_files in chat_images.items():
        # Se asegura de que tenemos exactamente tres imágenes por chat_id
        if len(image_files) == 3:
            # Comprueba si todas las imágenes existen en la carpeta de descargas
            all_files_exist = all(os.path.exists(os.path.join(descargas_path, img)) for img in image_files)

            if all_files_exist:
                # Mueve cada archivo de imagen a la carpeta de destino
                for img in image_files:
                    src = os.path.join(descargas_path, img)
                    dst = os.path.join(destino_path, img)
                    shutil.move(src, dst)

    time.sleep(intervalo_verificacion)  # Espera antes de la siguiente verificación
