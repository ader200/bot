import os
import json
import time

def verificar_nuevas_imagenes():
    # Verificar si hay imágenes en la carpeta imagenes1
    nombres_archivos_imagenes = os.listdir("inversion1")

    # Lista para almacenar los datos de las nuevas imágenes
    nuevas_imagenes = []

    try:
        # Leer todo el contenido del archivo JSON
        with open("invertir.json", "r") as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    except FileNotFoundError:
        print("Archivo 'invertir.json' no encontrado")
        return

    # Iterar sobre cada objeto en la lista JSON
    for numero_generado in datos:
        # Obtener el nombre de la imagen del número generado
        imagen_filename = numero_generado.get("imagen")

        # Verificar si la imagen está en la carpeta imagenes1
        if imagen_filename and os.path.isfile(os.path.join("inversion1", imagen_filename)):
            # Se encontró una nueva imagen, obtener los datos relevantes
            nombre = numero_generado.get("nombre")
            celular = numero_generado.get("celular")
            inversion = numero_generado.get("inversion")
            ganancia_calculada = numero_generado.get("ganancia_calculada")
            chat_id = numero_generado.get("chat_id")
            
            # Agregar los datos relevantes a la lista de nuevas imágenes
            nueva_imagen = {
                "nombre": nombre,
                "celular": celular,
                "inversion": inversion,
                "ganancia_calculada": ganancia_calculada,
                "imagen": imagen_filename,
                "chat_id": chat_id,
            }

            nuevas_imagenes.append(nueva_imagen)

    # Guardar la lista de nuevas imágenes en un archivo JSON
    with open("invertir1.json", "w") as inversion1_file:
        json.dump(nuevas_imagenes, inversion1_file, indent=4)  # indent=4 para una mejor legibilidad

# Ejecutar la verificación periódicamente
while True:
    verificar_nuevas_imagenes()
    # Esperar 10 segundos antes de volver a verificar
    time.sleep(5)
