import os
import json
from flask import Flask, render_template, redirect, url_for, request, send_from_directory
import subprocess
from datetime import datetime
import uuid

app = Flask(__name__)

IMAGENES_DIR = "imagenes"
IMAGENES1_DIR = "imagenes1"
BORRADORES_DIR = "borradores"
INVERSION_DIR = "inversion"
INVERSION1_DIR = "inversion1"
BORRADORES1_DIR = "borradores1"
TRABAJADORES_FILE = "trabajadores.json"
LISTA_FILE = "lista.json"
PAGA_FILE = "paga.json"

def read_json(file_path): 
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
                else:
                    return []
        except json.JSONDecodeError:
            return []
    return []


def write_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def verificar_limite_numeros():
    with open("limite_numeros.json", "r") as file:
        limite_numeros = json.load(file)
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

def mover_archivos(origen, destino):
    archivos = os.listdir(origen)
    for archivo in archivos:
        os.rename(os.path.join(origen, archivo), os.path.join(destino, archivo))

@app.route('/')
def index():
    imagenes = [f for f in os.listdir(IMAGENES_DIR) if os.path.isfile(os.path.join(IMAGENES_DIR, f))]
    inversiones = [f for f in os.listdir(INVERSION_DIR) if os.path.isfile(os.path.join(INVERSION_DIR, f))]
    trabajadores = read_json(TRABAJADORES_FILE)
    contratados = read_json(LISTA_FILE)
    return render_template('index.html', imagenes=imagenes, inversiones=inversiones, trabajadores=trabajadores, contratados=contratados)

@app.route('/imagenes/<filename>')
def imagenes(filename):
    return send_from_directory(IMAGENES_DIR, filename)

@app.route('/inversiones/<filename>')
def inversiones(filename):
    return send_from_directory(INVERSION_DIR, filename)

@app.route('/guardar/<filename>', methods=['POST'])
def guardar(filename):
    # Obtener el número de copias del formulario, restando 1 y manejando la excepción para valores 1, 0 o vacío
    num_copias = request.form.get('num_copias', '').strip()
    if num_copias == '':
        num_copias = 0
    else:
        num_copias = int(num_copias) - 1

    src = os.path.join(IMAGENES_DIR, filename)
    dst = os.path.join(IMAGENES1_DIR, filename)
    
    if num_copias > 0:
        imagenes2 = read_json("imagenes2.json")
        datos_imagen = next((img for img in imagenes2 if img["nombre_imagen"] == filename), None)
        
        if datos_imagen:
            for _ in range(num_copias):
                numero_unico = generar_numero_unico()
                if numero_unico:
                    datos_compra = {
                        "numero_unico": numero_unico,
                        "nombre": datos_imagen["nombre"],
                        "numero": datos_imagen["numero"],
                        "chat_id": datos_imagen["chat_id"],
                        "nombre_imagen": filename,
                        "fecha_registro": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Leer el contenido actual de numeros_generados.json
                    try:
                        with open("imagenes2.json", "r") as file:
                            numeros_generados = json.load(file)
                    except (json.JSONDecodeError, FileNotFoundError):
                        numeros_generados = []

                    # Agregar los nuevos datos
                    numeros_generados.append(datos_compra)

                    # Escribir de nuevo el archivo en el formato deseado
                    with open("imagenes2.json", "w") as file:
                        json.dump(numeros_generados, file, indent=4)
    
                    mover_archivos('imagenes', 'imagenes1')

    else:
        # Si num_copias es 0 o menos, o si es 1 (originalmente ingresado como 1), mueve el archivo.
        os.rename(src, dst)     

    return redirect(url_for('index'))

@app.route('/guardar_inversion/<filename>')
def guardar_inversion(filename):
    src = os.path.join(INVERSION_DIR, filename)
    dst = os.path.join(INVERSION1_DIR, filename)
    os.rename(src, dst)
    return redirect(url_for('index'))

@app.route('/borrar/<filename>')
def borrar(filename):
    src = os.path.join(IMAGENES_DIR, filename)
    dst = os.path.join(BORRADORES_DIR, filename)
    os.rename(src, dst)
    return redirect(url_for('index'))

@app.route('/borrar_inversion/<filename>')
def borrar_inversion(filename):
    src = os.path.join(INVERSION_DIR, filename)
    dst = os.path.join(BORRADORES1_DIR, filename)
    os.rename(src, dst)
    return redirect(url_for('index'))

@app.route('/guardar_trabajador/<int:index>')
def guardar_trabajador(index):
    trabajadores = read_json(TRABAJADORES_FILE)
    lista = read_json(LISTA_FILE)
    if 0 <= index < len(trabajadores):
        lista.append(trabajadores.pop(index))
        write_json(LISTA_FILE, lista)
        write_json(TRABAJADORES_FILE, trabajadores)
    return redirect(url_for('index'))

@app.route('/borrar_trabajador/<int:index>')
def borrar_trabajador(index):
    trabajadores = read_json(TRABAJADORES_FILE)
    if 0 <= index < len(trabajadores):
        trabajadores.pop(index)
        write_json(TRABAJADORES_FILE, trabajadores)
    return redirect(url_for('index'))

@app.route('/contratados')
def contratados():
    contratados = read_json(LISTA_FILE)
    return render_template('contratados.html', contratados=contratados)

@app.route('/calcular_pago/<int:index>', methods=['POST'])
def calcular_pago(index):
    contratados = read_json(LISTA_FILE)
    if 0 <= index < len(contratados):
        qr1_visits = int(request.form.get('qr1_visits', 0))
        qr2_visits = int(request.form.get('qr2_visits', 0))
        bot_visits = request.form.get('bot_visits', 0)
        bot_visits = int(bot_visits) if bot_visits else 0

        # Calculating the payment
        qr_payment = 0.03 * min(qr1_visits, qr2_visits)  # Only pay if both QR codes are visited
        bot_payment = 0.05 * bot_visits
        total_payment = qr_payment + bot_payment
        
        pago = {
            "nombre": contratados[index]["nombre"],
            "chat_id": contratados[index]["chat_id"],
            "fecha_y_hora": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_dinero": total_payment
        }

        paga = read_json(PAGA_FILE)
        paga.append(pago)
        write_json(PAGA_FILE, paga)
    return redirect(url_for('contratados'))



@app.route('/finalizar')
def finalizar():
    try:
        subprocess.Popen(["python", "4.py"])
    except Exception as e:
        print(f"Error al ejecutar 4.py: {e}")
    return redirect(url_for('index'))

@app.route('/finalizar_inversion')
def finalizar_inversion():
    try:
        subprocess.Popen(["python", "invertir2.py"])
    except Exception as e:
        print(f"Error al ejecutar invertir2.py: {e}")
    return redirect(url_for('index'))

@app.route('/siguiente', methods=['POST'])
def siguiente():
    try:
        subprocess.Popen(["python", "qrtemples.py"])
    except Exception as e:
        print(f"Error al ejecutar qrtemples.py: {e}")
    return redirect(url_for('index'))



if __name__ == '__main__':

    subprocess.Popen(["python", "add.py"])        
    subprocess.Popen(["python", "5.py"])  
    subprocess.Popen(["python", "invertir.py"])
    subprocess.Popen(["python", "invertir1.py"])
    subprocess.Popen(["python", "qr.py"])
    subprocess.Popen(["python", "qr1.py"])
    subprocess.Popen(["python", "mt.py"])
                     

    app.run(debug=True)
