from flask import Flask, render_template, request, jsonify, session
import json
from datetime import datetime, timedelta
import random
import os
import threading
import time
import subprocess
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import psutil
import logging
import sys

# Cargar variables de entorno
load_dotenv()

# Configurar logging para usar stdout/stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Inicializar variable global
rifa_process = None

# Constantes
DIAS_ESPERA = 20  # Días que debe esperar un código usado para volver a estar disponible

# Crear la aplicación Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para usar sesiones

# Iniciar rifa.py como subproceso
def iniciar_rifa():
    global rifa_process
    try:
        logger.info("Intentando iniciar rifa.py...")
        
        # Verificar si ya hay un proceso de rifa.py corriendo
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' and proc.info['cmdline'] and 'rifa.py' in proc.info['cmdline']:
                    logger.info("Ya hay una instancia de rifa.py corriendo")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # Intentar iniciar el proceso con reintentos
        max_retries = int(os.getenv('MAX_RETRIES', 3))
        retry_delay = int(os.getenv('RETRY_DELAY', 5))
        for attempt in range(max_retries):
            try:
                logger.info(f"Intento {attempt + 1} de {max_retries} para iniciar rifa.py")
                
                # Verificar que el archivo existe
                if not os.path.exists('rifa.py'):
                    raise FileNotFoundError("El archivo rifa.py no existe")
                
                # Verificar permisos
                if not os.access('rifa.py', os.R_OK):
                    raise PermissionError("No hay permisos para leer rifa.py")
                
                rifa_process = subprocess.Popen(
                    ["python", "rifa.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Esperar un momento para ver si el proceso se inicia correctamente
                time.sleep(2)
                
                if rifa_process.poll() is not None:
                    # El proceso terminó inmediatamente
                    stdout, stderr = rifa_process.communicate()
                    logger.error(f"Error en la salida del proceso: {stderr}")
                    raise Exception(f"El proceso terminó con código {rifa_process.returncode}")
                
                logger.info(f"rifa.py iniciado correctamente como subproceso (PID: {rifa_process.pid})")
                return
                
            except Exception as e:
                logger.error(f"Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Se alcanzó el número máximo de reintentos")
                    rifa_process = None
                    raise
                    
    except Exception as e:
        logger.error(f"Error fatal al iniciar rifa.py: {str(e)}")
        rifa_process = None
        raise

def verificar_rifa():
    global rifa_process
    while True:
        try:
            if rifa_process is None or rifa_process.poll() is not None:
                logger.warning("rifa.py no está corriendo, intentando reiniciar...")
                iniciar_rifa()
            time.sleep(60)  # Verificar cada minuto
        except Exception as e:
            logger.error(f"Error en el proceso de verificación: {e}")
            time.sleep(60)  # Esperar un minuto antes de reintentar

# Iniciar el proceso de verificación en un hilo separado
threading.Thread(target=verificar_rifa, daemon=True).start()

# Iniciar rifa.py inicialmente
iniciar_rifa()

# Conexión a MongoDB
try:
    uri = os.getenv('MONGODB_URI')
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    codigos_collection = db.codigos
    print("Conexión a MongoDB establecida correctamente")
except Exception as e:
    print(f"Error al conectar con MongoDB: {e}")
    db = None

def inicializar_codigos():
    """Inicializa la estructura de códigos en MongoDB si no existe"""
    try:
        datos = codigos_collection.find_one()
        if not datos:
            # Si no hay datos, crear estructura inicial
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
            codigos_collection.insert_one(estructura_inicial)
            return estructura_inicial
        else:
            # Verificar y corregir la estructura si es necesario
            estructura_correcta = {
                'codigos_disponibles': datos.get('codigos_disponibles', []),
                'codigos_usados': datos.get('codigos_usados', []),
                'codigos_activos': datos.get('codigos_activos', {
                    'pagina1': {'codigo': None, 'fecha_asignacion': None, 'fecha_ultimo_uso': None, 'usos': 0},
                    'pagina2': {'codigo': None, 'fecha_asignacion': None, 'fecha_ultimo_uso': None, 'usos': 0},
                    'pagina3': {'codigo': None, 'fecha_asignacion': None, 'fecha_ultimo_uso': None, 'usos': 0},
                    'pagina4': {'codigo': None, 'fecha_asignacion': None, 'fecha_ultimo_uso': None, 'usos': 0}
                }),
                'estadisticas': datos.get('estadisticas', {
                    'total_codigos_generados': 0,
                    'codigos_disponibles': 0,
                    'codigos_usados': 0,
                    'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            }
            
            # Actualizar estadísticas
            estructura_correcta['estadisticas'].update({
                'codigos_disponibles': len(estructura_correcta['codigos_disponibles']),
                'codigos_usados': len(estructura_correcta['codigos_usados']),
                'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Actualizar en la base de datos si hay cambios
            if estructura_correcta != datos:
                codigos_collection.update_one({}, {'$set': estructura_correcta})
                print("Estructura de datos actualizada en MongoDB")
            
            return estructura_correcta
    except Exception as e:
        print(f"Error al inicializar códigos: {e}")
        return None

def cargar_codigos():
    """Carga los códigos de MongoDB"""
    try:
        datos = codigos_collection.find_one()
        if not datos:
            datos = inicializar_codigos()
        if not datos:
            raise Exception("No se pudieron cargar los datos de la base de datos")
        
        # Verificar que hay códigos disponibles
        if not datos.get('codigos_disponibles'):
            print("No hay códigos disponibles en la base de datos")
            return None
            
        return datos
    except Exception as e:
        print(f"Error al cargar códigos: {e}")
        return None

def guardar_codigos(datos):
    """Guarda los códigos en MongoDB"""
    try:
        # Actualizar estadísticas
        datos['estadisticas'].update({
            'codigos_disponibles': len(datos['codigos_disponibles']),
            'codigos_usados': len(datos['codigos_usados']),
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        codigos_collection.update_one({}, {'$set': datos})
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
    try:
        datos = cargar_codigos()
        if not datos:
            print("No se pudieron cargar los datos")
            return None

        # Liberar códigos antiguos primero
        liberar_codigos_antiguos()
        
        # Recargar datos después de liberar códigos
        datos = cargar_codigos()
        if not datos:
            return None
        
        # Verificar si ya hay un código activo para esta página
        pagina_key = f'pagina{pagina}'
        if pagina_key not in datos['codigos_activos']:
            print(f"Error: No se encontró la página {pagina_key}")
            return None
            
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

def verificar_codigos_mongodb():
    """Verifica los códigos en MongoDB y muestra su estado"""
    try:
        datos = codigos_collection.find_one()
        if datos:
            print("\nEstado actual de los códigos en MongoDB:")
            print(f"Códigos disponibles: {len(datos.get('codigos_disponibles', []))}")
            print(f"Códigos usados: {len(datos.get('codigos_usados', []))}")
            print(f"Total de códigos: {len(datos.get('codigos_disponibles', [])) + len(datos.get('codigos_usados', []))}")
            print(f"Última actualización: {datos.get('estadisticas', {}).get('ultima_actualizacion', 'No disponible')}")
            return True
        else:
            print("No se encontraron datos en MongoDB")
            return False
    except Exception as e:
        print(f"Error al verificar códigos en MongoDB: {e}")
        return False

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
    # Verificar el estado de los códigos en MongoDB
    verificar_codigos_mongodb()
    # Inicializar la estructura de códigos en MongoDB
    inicializar_codigos()
    # Ejecutar en modo desarrollo
    app.run(debug=True, host='0.0.0.0', port=8000)