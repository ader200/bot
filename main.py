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
    app = Flask(__name__)
      
      # Conexión a MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.rifa_db

  

    ARCHIVO_CODIGOS = 'codigos.json'

    def cargar_codigos():
        """Carga los códigos del archivo JSON"""
        if not os.path.exists(ARCHIVO_CODIGOS):
            return None
        with open(ARCHIVO_CODIGOS, 'r') as f:
            return json.load(f)

    def guardar_codigos(datos):
        """Guarda los códigos en el archivo JSON"""
        with open(ARCHIVO_CODIGOS, 'w') as f:
            json.dump(datos, f, indent=4)

    def actualizar_codigo_activo():
        """Actualiza el código activo si es necesario"""
        datos = cargar_codigos()
        if not datos:
            return None

        ahora = datetime.now()
        hoy = ahora.strftime('%Y-%m-%d')
        
        # Si ya hay un código activo para hoy y no está usado, retornarlo
        if datos['fecha_activo'] == hoy and datos['codigo_activo']:
            # Verificar si el código no está en usados
            if not any(usado['codigo'] == datos['codigo_activo'] for usado in datos['usados']):
                return datos['codigo_activo']
        
        # Liberar códigos usados después de 30 días
        if datos['usados']:
            fecha_limite = (ahora - timedelta(days=30)).strftime('%Y-%m-%d')
            nuevos_usados = []
            
            for codigo in datos['usados']:
                if codigo['fecha'] < fecha_limite:
                    datos['codigos'].append(codigo['codigo'])
                else:
                    nuevos_usados.append(codigo)
            
            datos['usados'] = nuevos_usados

        # Seleccionar nuevo código activo solo si no hay uno activo o si el actual está usado
        if not datos['codigo_activo'] or any(usado['codigo'] == datos['codigo_activo'] for usado in datos['usados']):
            if datos['codigos']:
                nuevo_activo = random.choice(datos['codigos'])
                datos['codigos'].remove(nuevo_activo)
                datos['codigo_activo'] = nuevo_activo
                datos['fecha_activo'] = hoy
                guardar_codigos(datos)
                return nuevo_activo
        
        return datos['codigo_activo']

    def verificar_codigo(codigo):
        """Verifica si un código es válido y está activo"""
        datos = cargar_codigos()
        if not datos:
            return {'valido': False, 'mensaje': 'Error al cargar códigos'}
        
        # Verificar si el código coincide con el activo
        if codigo == datos['codigo_activo']:
            # Verificar si ya fue usado
            if any(usado['codigo'] == codigo for usado in datos['usados']):
                return {'valido': False, 'mensaje': 'Este código ya ha sido utilizado'}
            return {'valido': True, 'mensaje': 'Código válido'}
        
        return {'valido': False, 'mensaje': 'Código no válido o inactivo'}

    def marcar_codigo_usado(codigo):
        """Marca un código como usado"""
        datos = cargar_codigos()
        if not datos or codigo != datos['codigo_activo']:
            return False
        
        # Verificar si ya está usado
        if any(usado['codigo'] == codigo for usado in datos['usados']):
            return False
        
        # Agregar a usados
        datos['usados'].append({
            'codigo': codigo,
            'fecha': datetime.now().strftime('%Y-%m-%d')
        })
        
        # Limpiar código activo
        datos['codigo_activo'] = None
        datos['fecha_activo'] = None
        
        guardar_codigos(datos)
        return True

    def actualizar_codigo_periodicamente():
        """Función que se ejecuta en un hilo separado para actualizar el código cada minuto"""
        while True:
            actualizar_codigo_activo()
            time.sleep(60)  # Esperar 1 minuto

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
        codigo = actualizar_codigo_activo()
        return jsonify({'codigo': codigo})

    # Iniciar el hilo que actualiza el código periódicamente
    actualizador = threading.Thread(target=actualizar_codigo_periodicamente, daemon=True)
    actualizador.start()
    
    # Iniciar la aplicación Flask
    app.run(debug=True, host='0.0.0.0', port=8000)

if __name__ == '__main__':
    main_app()
