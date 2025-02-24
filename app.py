from flask import Flask, request, jsonify, render_template
from pulp import *
import numpy as np
import time

app = Flask(__name__)

# Ruta principal - Sirve la interfaz web
@app.route('/')
def home():
    return render_template('index.html')

# Ruta de optimización
@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        result = calcular_optimizacion(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calcular_optimizacion(data):
    # 1. Extraer datos del frontend
    largo_material = data['materialLength']
    articulos = data['articles']
    
    # 2. Configurar modelo de optimización
    prob = LpProblem("Problema_Corte", LpMinimize)
    
    # 3. Variables de decisión
    max_barras = 100  # Límite máximo de barras a considerar
    y = LpVariable.dicts("BarraEnUso", range(max_barras), 0, 1, LpInteger)
    x = LpVariable.dicts("Cantidad", 
                       [(i, j) for i in range(len(articulos)) for j in range(max_barras)], 
                       0, None, LpInteger)
    
    # 4. Función objetivo
    prob += lpSum(y[j] for j in range(max_barras))
    
    # 5. Restricciones
    for i in range(len(articulos)):
        prob += lpSum(x[(i, j)] for j in range(max_barras)) >= articulos[i]['quantity']
        
    for j in range(max_barras):
        prob += lpSum(x[(i, j)] * articulos[i]['length'] 
                   for i in range(len(articulos))) <= largo_material * y[j]
    
    # 6. Resolver
    start_time = time.time()
    prob.solve()
    tiempo_ejecucion = time.time() - start_time
    
    # 7. Procesar resultados
    barras = []
    if LpStatus[prob.status] == "Optimal":
        for j in range(max_barras):
            if value(y[j]) == 1:
                detalle_barra = []
                total_usado = 0
                for i in range(len(articulos)):
                    cantidad = value(x[(i, j)])
                    if cantidad > 0:
                        detalle_barra.append({
                            "name": articulos[i]['name'],
                            "length": articulos[i]['length'],
                            "quantity": int(cantidad)
                        })
                        total_usado += articulos[i]['length'] * cantidad
                desperdicio = largo_material - total_usado
                barras.append({
                    "barra_id": j+1,
                    "total_usado": total_usado,
                    "desperdicio": desperdicio,
                    "detalle": detalle_barra
                })
    
    # 8. Ordenar por desperdicio
    barras.sort(key=lambda x: x['desperdicio'])
    
    return {
        "tiempo_ejecucion": round(tiempo_ejecucion, 2),
        "total_barras": len(barras),
        "barras": barras
    }

if __name__ == '__main__':
    app.run(debug=True)