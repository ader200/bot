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
LINKS_FILE = 'links.json'

# Iniciar el bot de Telegram
def iniciar_bot():
    try:
        subprocess.Popen(["python", "rifa.py"])
        print("Bot iniciado correctamente")
    except Exception as e:
        print(f"Error al iniciar el bot: {e}")

# Cargar links de páginas web
def cargar_links():
    try:
        with open(LINKS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

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
        'fecha_expiracion': (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
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
            if datetime.now() < fecha_expiracion:
                return True
    return False

# Ruta principal
@app.route('/')
def index():
    links = cargar_links()
    if not links:
        return "No hay páginas web configuradas"
    return render_template('index.html', links=links)

# Ruta para verificar código
@app.route('/verificar', methods=['POST'])
def verificar():
    codigo = request.form.get('codigo')
    if verificar_codigo(codigo):
        return jsonify({'valido': True})
    return jsonify({'valido': False})

# Ruta para obtener nuevo código
@app.route('/nuevo_codigo')
def nuevo_codigo():
    return jsonify({'codigo': actualizar_codigo()})

# Ruta para agregar nuevo link (solo admin)
@app.route('/admin/agregar_link', methods=['POST'])
def agregar_link():
    link = request.form.get('link')
    if link:
        links = cargar_links()
        if link not in links:
            links.append(link)
            with open(LINKS_FILE, 'w') as f:
                json.dump(links, f)
        return jsonify({'success': True})
    return jsonify({'success': False})

# Ruta para eliminar link (solo admin)
@app.route('/admin/eliminar_link', methods=['POST'])
def eliminar_link():
    link = request.form.get('link')
    if link:
        links = cargar_links()
        if link in links:
            links.remove(link)
            with open(LINKS_FILE, 'w') as f:
                json.dump(links, f)
        return jsonify({'success': True})
    return jsonify({'success': False})

# Iniciar el bot al arrancar la aplicación
if __name__ == '__main__':
    iniciar_bot()
    app.run(host='0.0.0.0', port=8000)
