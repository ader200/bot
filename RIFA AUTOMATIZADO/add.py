import os
import json
import time

def verificar_nuevas_imagenes():
    # Verificar si hay imágenes en la carpeta imagenes1
    nombres_archivos_imagenes = os.listdir("imagenes1")

    # Lista para almacenar los datos de las nuevas imágenes
    nuevas_imagenes = []

    # Leer el archivo JSON completo
    with open("imagenes2.json") as f:
        try:
            numeros_generados = json.load(f)
        except json.JSONDecodeError as e:
            print("Error de formato JSON en el archivo:", e)
            return

    # Procesar cada objeto en el JSON
    for numero_generado in numeros_generados:
        # Obtener el nombre de la imagen del número generado
        imagen = numero_generado.get("nombre_imagen")

        # Verificar si la imagen está en la carpeta imagenes1
        if imagen and os.path.isfile(os.path.join("imagenes1", imagen)):
            # Se encontró una nueva imagen, obtener los datos relevantes
            nombre = numero_generado.get("nombre")
            numero = numero_generado.get("numero")
            chat_id = numero_generado.get("chat_id")

            # Agregar los datos relevantes a la lista de nuevas imágenes
            nueva_imagen = {
                "numero_unico": numero_generado["numero_unico"],
                "nombre": nombre,
                "numero": numero,
                "chat_id": chat_id,
                "nombre_imagen": imagen
            }
            nuevas_imagenes.append(nueva_imagen)

    # Guardar la lista de nuevas imágenes en un archivo JSON
    with open("imagenes1.json", "w") as imagenes1_file:
        json.dump(nuevas_imagenes, imagenes1_file, indent=4)  # indent=4 para una mejor legibilidad

# Ejecutar la verificación periódicamente
while True:
    verificar_nuevas_imagenes()
    # Esperar 10 segundos antes de volver a verificar
    time.sleep(5)
