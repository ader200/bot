from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import random
import string
import time
import subprocess
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Archivo para almacenar los códigos y su estado
CODIGOS_FILE = 'codigos.json'

# Iniciar el bot de Telegram
def iniciar_bot():
    try:
        subprocess.Popen(["python", "rifa.py"])
        print("Bot iniciado correctamente")
    except Exception as e:
        print(f"Error al iniciar el bot: {e}")

# Generar código aleatorio
def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Cargar códigos existentes
def cargar_codigos():
    try:
        with open(CODIGOS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

# Guardar códigos
def guardar_codigos(codigos):
    with open(CODIGOS_FILE, 'w') as f:
        json.dump(codigos, f)

# Generar nuevo código y guardarlo
def actualizar_codigo():
    codigos = cargar_codigos()
    nuevo_codigo = generar_codigo()
    codigos[nuevo_codigo] = {
        'activo': True,
        'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'fecha_expiracion': (datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'tiempo_espera': (datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
    }
    guardar_codigos(codigos)
    return nuevo_codigo

# Verificar si un código es válido
def verificar_codigo(codigo):
    codigos = cargar_codigos()
    if codigo in codigos:
        codigo_info = codigos[codigo]
        if codigo_info['activo']:
            fecha_expiracion = datetime.strptime(codigo_info['fecha_expiracion'], '%Y-%m-%d %H:%M:%S')
            tiempo_espera = datetime.strptime(codigo_info['tiempo_espera'], '%Y-%m-%d %H:%M:%S')
            ahora = datetime.now()
            
            if ahora > fecha_expiracion:
                return {'valido': False, 'mensaje': 'Código expirado'}
            elif ahora < tiempo_espera:
                tiempo_restante = int((tiempo_espera - ahora).total_seconds())
                return {'valido': False, 'mensaje': f'Espera {tiempo_restante} segundos antes de usar el código'}
            else:
                return {'valido': True, 'mensaje': 'Código válido'}
    return {'valido': False, 'mensaje': 'Código no válido'}

# Rutas para las páginas web
@app.route('/')
def index():
    return render_template('index.html', numero_pagina=1)

@app.route('/pagina2')
def pagina2():
    return render_template('index.html', numero_pagina=2)

@app.route('/pagina3')
def pagina3():
    return render_template('index.html', numero_pagina=3)

@app.route('/pagina4')
def pagina4():
    return render_template('index.html', numero_pagina=4)

# Ruta para verificar código
@app.route('/verificar', methods=['POST'])
def verificar():
    codigo = request.form.get('codigo')
    resultado = verificar_codigo(codigo)
    return jsonify(resultado)

# Ruta para obtener nuevo código
@app.route('/nuevo_codigo')
def nuevo_codigo():
    return jsonify({'codigo': actualizar_codigo()})

# Iniciar el bot al arrancar la aplicación
if __name__ == '__main__':
    iniciar_bot()
    app.run(host='0.0.0.0', port=8000)
