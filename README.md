# Sistema de Rifas Automatizado

Este es un sistema completo de rifas que incluye un bot de Telegram y una página web para la gestión de rifas gratuitas.

## Características

- Bot de Telegram para gestionar rifas pagadas y gratuitas
- Página web con sistema de autenticación para rifas gratuitas
- Generación automática de códigos que cambian cada 10 minutos
- Sistema de verificación de comprobantes de pago
- Generación de códigos QR para los boletos
- Panel de administración para gestionar ganadores
- Sistema de múltiples páginas web para distribución de códigos

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta de Telegram con un bot creado
- Cuenta en Render.com para el despliegue

## Instalación

1. Clona este repositorio:
```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_DIRECTORIO>
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las variables de entorno:
- Crea un archivo `.env` con las siguientes variables:
```
TELEGRAM_BOT_TOKEN=tu_token_aqui
ADMIN_CHAT_ID=tu_id_aqui
```

## Uso Local

1. Inicia el servidor web:
```bash
python main.py
```

2. El bot de Telegram se iniciará automáticamente junto con el servidor web.

## Despliegue en Render.com

1. Crea una cuenta en Render.com si no tienes una.

2. Crea un nuevo servicio Web:
   - Conecta tu repositorio de GitHub
   - Selecciona la rama principal
   - Configura el comando de inicio:
     ```
     gunicorn main:app
     ```
   - Configura las variables de entorno necesarias

3. El servicio se desplegará automáticamente y proporcionará una URL para acceder a la web.

## Comandos del Bot

### Comandos Generales
- `/start` - Muestra el mensaje de bienvenida y comandos disponibles
- `/rifa` - Inicia el proceso de compra de una rifa
- `/gratis` - Inicia el proceso para obtener una rifa gratis

### Comandos de Administrador
- `/ganador` - Selecciona un ganador aleatorio de las rifas pagadas
- `/ganadorz` - Selecciona un ganador aleatorio de las rifas gratuitas
- `/qe` - Agrega un nuevo link de página web para distribución de códigos

## Estructura de Archivos

- `main.py` - Servidor web Flask
- `rifa.py` - Bot de Telegram
- `templates/index.html` - Plantilla de la página web
- `requirements.txt` - Dependencias del proyecto
- `*.json` - Archivos de almacenamiento de datos

## Notas Importantes

- Los códigos de rifas gratuitas cambian cada 10 minutos
- Los códigos tienen una validez de 5 minutos después de ser mostrados
- El administrador debe verificar manualmente los comprobantes de pago
- Los ganadores son seleccionados aleatoriamente por el administrador

## Soporte

Para cualquier problema o consulta, por favor abre un issue en el repositorio. 