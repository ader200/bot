from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime, timedelta
import random
import os
import threading
import time
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def main_app():
    # Conexión a MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.rifa_db

    app = Flask(__name__)

    ARCHIVO_CODIGOS = 'codigos.json'
    ARCHIVO_MOSTRADOS = 'codigos_mostrados.json'

    def inicializar_archivos():
        """Inicializa los archivos JSON si no existen"""
        if not os.path.exists(ARCHIVO_MOSTRADOS):
            with open(ARCHIVO_MOSTRADOS, 'w') as f:
                json.dump({
                    "codigos_mostrados": [],
                    "ultimo_codigo": None,
                    "ultima_actualizacion": None
                }, f, indent=4)

    def cargar_codigos():
        """Carga los códigos del archivo JSON"""
        if not os.path.exists(ARCHIVO_CODIGOS):
            return None
        with open(ARCHIVO_CODIGOS, 'r') as f:
            return json.load(f)

    def cargar_mostrados():
        """Carga el registro de códigos mostrados"""
        with open(ARCHIVO_MOSTRADOS, 'r') as f:
            return json.load(f)

    def guardar_mostrados(datos):
        """Guarda el registro de códigos mostrados"""
        with open(ARCHIVO_MOSTRADOS, 'w') as f:
            json.dump(datos, f, indent=4)

    def obtener_nuevo_codigo():
        """Obtiene un nuevo código aleatorio que no haya sido mostrado"""
        datos = cargar_codigos()
        mostrados = cargar_mostrados()
        
        if not datos:
            return None

        # Obtener códigos disponibles (los que no están en mostrados)
        codigos_disponibles = [c for c in datos['codigos'] if c not in mostrados['codigos_mostrados']]
        
        # Si no hay códigos disponibles, reiniciar la lista
        if not codigos_disponibles:
            mostrados['codigos_mostrados'] = []
            codigos_disponibles = datos['codigos']
        
        # Seleccionar un código aleatorio
        if codigos_disponibles:
            nuevo_codigo = random.choice(codigos_disponibles)
            mostrados['codigos_mostrados'].append(nuevo_codigo)
            mostrados['ultimo_codigo'] = nuevo_codigo
            mostrados['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            guardar_mostrados(mostrados)
            return nuevo_codigo
            
        return None

    def actualizar_codigo_periodicamente():
        """Función que se ejecuta en un hilo separado para actualizar el código cada minuto"""
        while True:
            obtener_nuevo_codigo()
            time.sleep(60)  # Esperar 1 minuto

    def verificar_codigo(codigo):
        """Verifica si un código es válido"""
        mostrados = cargar_mostrados()
        if not mostrados or not mostrados['ultimo_codigo']:
            return {'valido': False, 'mensaje': 'No hay código activo'}
        
        if codigo == mostrados['ultimo_codigo']:
            # Verificar si ya fue usado
            datos = cargar_codigos()
            if any(usado['codigo'] == codigo for usado in datos['usados']):
                return {'valido': False, 'mensaje': 'Este código ya ha sido utilizado'}
            return {'valido': True, 'mensaje': 'Código válido'}
        
        return {'valido': False, 'mensaje': 'Código no válido o inactivo'}

    def marcar_codigo_usado(codigo):
        """Marca un código como usado"""
        datos = cargar_codigos()
        mostrados = cargar_mostrados()
        
        if not datos or codigo != mostrados['ultimo_codigo']:
            return False
        
        # Verificar si ya está usado
        if any(usado['codigo'] == codigo for usado in datos['usados']):
            return False
        
        # Agregar a usados
        datos['usados'].append({
            'codigo': codigo,
            'fecha': datetime.now().strftime('%Y-%m-%d')
        })
        
        with open(ARCHIVO_CODIGOS, 'w') as f:
            json.dump(datos, f, indent=4)
        
        return True

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

    @app.route('/verificar', methods=['POST'])
    def verificar():
        codigo = request.form.get('codigo')
        if not codigo:
            return jsonify({'valido': False, 'mensaje': 'Código no proporcionado'})
        
        resultado = verificar_codigo(codigo)
        if resultado['valido']:
            marcar_codigo_usado(codigo)
        
        return jsonify(resultado)

    @app.route('/codigo_activo')
    def obtener_codigo_activo():
        mostrados = cargar_mostrados()
        return jsonify({'codigo': mostrados['ultimo_codigo'] if mostrados else None})

    # Inicializar archivos
    inicializar_archivos()

    # Iniciar el hilo que actualiza el código periódicamente
    actualizador = threading.Thread(target=actualizar_codigo_periodicamente, daemon=True)
    actualizador.start()
    
    # Iniciar la aplicación Flask
    app.run(debug=True, host='0.0.0.0', port=8000)

if __name__ == '__main__':
    main_app()