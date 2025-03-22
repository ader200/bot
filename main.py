from flask import Flask, render_template, request, jsonify, session
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

# Constantes
ARCHIVO_CODIGOS = 'codigos.json'
DIAS_ESPERA = 20  # Días que debe esperar un código usado para volver a estar disponible

# Crear la aplicación Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para usar sesiones

# Conexión a MongoDB
try:
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.rifa_db
except Exception as e:
    print(f"Error al conectar con MongoDB: {e}")
    db = None

def inicializar_json():
    """Crea la estructura inicial del archivo JSON si no existe"""
    estructura_inicial = {
        'codigos_disponibles': [],
        'codigos_usados': [],
        'codigos_activos': {
            'pagina1': {
                'codigo': None,
                'fecha_asignacion': None,
                'fecha_ultimo_uso': None,
                'usos': 0
            },
            'pagina2': {
                'codigo': None,
                'fecha_asignacion': None,
                'fecha_ultimo_uso': None,
                'usos': 0
            },
            'pagina3': {
                'codigo': None,
                'fecha_asignacion': None,
                'fecha_ultimo_uso': None,
                'usos': 0
            },
            'pagina4': {
                'codigo': None,
                'fecha_asignacion': None,
                'fecha_ultimo_uso': None,
                'usos': 0
            }
        },
        'estadisticas': {
            'total_codigos_generados': 0,
            'codigos_disponibles': 0,
            'codigos_usados': 0,
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    try:
        with open(ARCHIVO_CODIGOS, 'w') as f:
            json.dump(estructura_inicial, f, indent=4)
        return estructura_inicial
    except Exception as e:
        print(f"Error al inicializar JSON: {e}")
        return None

def cargar_codigos():
    """Carga los códigos del archivo JSON"""
    try:
        if not os.path.exists(ARCHIVO_CODIGOS):
            print("El archivo codigos.json no existe. Por favor, créalo primero usando codigos.py")
            return None
        
        with open(ARCHIVO_CODIGOS, 'r') as f:
            datos = json.load(f)
            # Verificar que la estructura sea correcta
            campos_requeridos = ['codigos_disponibles', 'codigos_usados', 'codigos_activos', 'estadisticas']
            if not all(campo in datos for campo in campos_requeridos):
                print("Estructura JSON incorrecta")
                return None
            return datos
    except Exception as e:
        print(f"Error al cargar códigos: {e}")
        return None

def guardar_codigos(datos):
    """Guarda los códigos en el archivo JSON"""
    try:
        campos_requeridos = ['codigos_disponibles', 'codigos_usados', 'codigos_activos', 'estadisticas']
        if not all(campo in datos for campo in campos_requeridos):
            print("Datos incompletos, no se pueden guardar")
            return False
            
        # Actualizar estadísticas
        datos['estadisticas'].update({
            'codigos_disponibles': len(datos['codigos_disponibles']),
            'codigos_usados': len(datos['codigos_usados']),
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
            
        with open(ARCHIVO_CODIGOS, 'w') as f:
            json.dump(datos, f, indent=4)
        return True
    except Exception as e:
        print(f"Error al guardar códigos: {e}")
        return False

def liberar_codigos_antiguos():
    """Libera los códigos que han estado usados por más de DIAS_ESPERA días"""
    datos = cargar_codigos()
    if not datos:
        return False

    fecha_limite = (datetime.now() - timedelta(days=DIAS_ESPERA)).strftime('%Y-%m-%d')
    codigos_liberados = []
    
    # Identificar códigos a liberar
    nuevos_usados = []
    for usado in datos['codigos_usados']:
        if usado['fecha'] < fecha_limite:
            codigos_liberados.append(usado['codigo'])
        else:
            nuevos_usados.append(usado)
    
    # Actualizar listas
    datos['codigos_usados'] = nuevos_usados
    datos['codigos_disponibles'].extend(codigos_liberados)
    
    # Guardar cambios
    return guardar_codigos(datos)

def obtener_nuevo_codigo(pagina):
    """Obtiene un nuevo código aleatorio para una página específica"""
    datos = cargar_codigos()
    if not datos:
        print("No se pudieron cargar los datos")
        return None

    # Liberar códigos antiguos primero
    liberar_codigos_antiguos()
    
    # Recargar datos después de liberar códigos
    datos = cargar_codigos()
    
    # Verificar si ya hay un código activo para esta página
    pagina_key = f'pagina{pagina}'
    codigo_actual = datos['codigos_activos'][pagina_key]['codigo']
    fecha_asignacion = datos['codigos_activos'][pagina_key]['fecha_asignacion']
    
    # Obtener la fecha y hora actual
    ahora = datetime.now()
    
    # Si hay un código activo, verificar si necesita ser cambiado
    if codigo_actual and fecha_asignacion:
        fecha_asignacion = datetime.strptime(fecha_asignacion, '%Y-%m-%d %H:%M:%S')
        # Verificar si es un nuevo día y si ya pasó la 1 AM
        if (ahora.date() > fecha_asignacion.date() and 
            ahora.hour >= 1):
            # Necesitamos un nuevo código
            codigo_actual = None
    
    if codigo_actual:
        # Actualizar fecha de último uso
        datos['codigos_activos'][pagina_key]['fecha_ultimo_uso'] = ahora.strftime('%Y-%m-%d %H:%M:%S')
        datos['codigos_activos'][pagina_key]['usos'] += 1
        guardar_codigos(datos)
        return codigo_actual

    # Verificar si hay códigos disponibles
    if not datos['codigos_disponibles']:
        print("No hay códigos disponibles")
        return None

    try:
        # Seleccionar un nuevo código aleatorio
        nuevo_codigo = random.choice(datos['codigos_disponibles'])
        
        # Remover el código de disponibles
        datos['codigos_disponibles'].remove(nuevo_codigo)
        
        # Agregar a usados
        datos['codigos_usados'].append({
            'codigo': nuevo_codigo,
            'fecha': ahora.strftime('%Y-%m-%d')
        })
        
        # Actualizar código activo para esta página
        datos['codigos_activos'][pagina_key].update({
            'codigo': nuevo_codigo,
            'fecha_asignacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_ultimo_uso': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'usos': 1
        })
        
        # Guardar cambios
        if not guardar_codigos(datos):
            print("Error al guardar los cambios")
            return None
            
        return nuevo_codigo
    except Exception as e:
        print(f"Error al obtener nuevo código: {e}")
        return None

def verificar_codigo(codigo, pagina):
    """Verifica si un código es válido para una página específica"""
    datos = cargar_codigos()
    if not datos:
        return {'valido': False, 'mensaje': 'Error al cargar códigos'}
    
    # Verificar si el código coincide con el activo de la página
    pagina_key = f'pagina{pagina}'
    if codigo == datos['codigos_activos'][pagina_key]['codigo']:
        return {'valido': True, 'mensaje': 'Código válido'}
    
    return {'valido': False, 'mensaje': 'Código no válido'}

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

@app.route('/verificar/<int:pagina>', methods=['POST'])
def verificar_por_pagina(pagina):
    if pagina not in [1, 2, 3, 4]:
        return jsonify({'valido': False, 'mensaje': 'Página no válida'}), 400
        
    codigo = request.form.get('codigo')
    if not codigo:
        return jsonify({'valido': False, 'mensaje': 'Código no proporcionado'})
    
    return jsonify(verificar_codigo(codigo, pagina))

@app.route('/codigo_activo/<int:pagina>')
def obtener_codigo_activo(pagina):
    if pagina not in [1, 2, 3, 4]:
        return jsonify({'error': 'Página no válida'}), 400
        
    codigo = obtener_nuevo_codigo(pagina)
    if codigo is None:
        return jsonify({'error': 'No hay códigos disponibles'}), 404
    return jsonify({'codigo': codigo})

if __name__ == '__main__':
    # Verificar que el archivo JSON existe
    if not os.path.exists(ARCHIVO_CODIGOS):
        print("ERROR: El archivo codigos.json no existe. Por favor, créalo primero usando codigos.py")
        exit(1)
    # Ejecutar en modo desarrollo
    app.run(debug=True, host='0.0.0.0', port=8000)