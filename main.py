from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import random
import string
import time
import subprocess
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Conexión a MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.rifa_db

# Colecciones
codigos_collection = db.codigos
registro_collection = db.registro
compras_collection = db.compras
ganadores_collection = db.ganadores
gratis_collection = db.gratis
links_collection = db.links

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

# Generar nuevo código y guardarlo
def actualizar_codigo():
    nuevo_codigo = generar_codigo()
    codigo_data = {
        'codigo': nuevo_codigo,
        'activo': True,
        'fecha_creacion': datetime.now(),
        'fecha_expiracion': datetime.now() + timedelta(minutes=1),
        'tiempo_espera': datetime.now() + timedelta(minutes=1)
    }
    codigos_collection.insert_one(codigo_data)
    return nuevo_codigo

# Verificar si un código es válido
def verificar_codigo(codigo):
    codigo_info = codigos_collection.find_one({'codigo': codigo})
    if codigo_info:
        ahora = datetime.now()
        fecha_expiracion = codigo_info['fecha_expiracion']
        tiempo_espera = codigo_info['tiempo_espera']
        
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

# Ruta para limpiar códigos antiguos (cada hora)
@app.route('/limpiar_codigos')
def limpiar_codigos():
    fecha_limite = datetime.now() - timedelta(hours=1)
    codigos_collection.delete_many({'fecha_creacion': {'$lt': fecha_limite}})
    return jsonify({'mensaje': 'Códigos antiguos eliminados'})

# Iniciar el bot al arrancar la aplicación
if __name__ == '__main__':
    iniciar_bot()
    app.run(host='0.0.0.0', port=8000)
