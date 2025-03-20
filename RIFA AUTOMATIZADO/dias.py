import datetime

# Número de días a seleccionar
num_dias = 5

# Lista para almacenar las fechas seleccionadas
fechas_seleccionadas = []

# Recorre todos los meses del año
for mes in range(1, 13):
    # Calcula el número de días en el mes actual
    if mes == 12:  # If the current month is December
        num_dias_mes = (datetime.date(2025, 1, 1) - datetime.date(2024, mes, 1)).days
    else:
        num_dias_mes = (datetime.date(2024, mes + 1, 1) - datetime.date(2024, mes, 1)).days
    
    # Calcula el intervalo de días
    intervalo = num_dias_mes // (num_dias - 1)
    
    # Selecciona las fechas en el mes actual
    for i in range(num_dias):
        dia = 1 + i * intervalo
        fechas_seleccionadas.append(datetime.date(2024, mes, dia))

# Imprime las fechas seleccionadas
for fecha in fechas_seleccionadas:
    print(fecha)
