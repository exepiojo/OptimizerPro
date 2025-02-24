import os
from flask import Flask, request, jsonify, render_template
from pulp import *
import numpy as np
import time

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        result = calcular_optimizacion(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calcular_optimizacion(data):
    largo_material = data['materialLength']
    articulos = data['articles']
    
    prob = LpProblem("Problema_Corte", LpMinimize)
    
    max_barras = 100  
    y = LpVariable.dicts("BarraEnUso", range(max_barras), 0, 1, LpInteger)
    x = LpVariable.dicts("Cantidad", 
                       [(i, j) for i in range(len(articulos)) for j in range(max_barras)], 
                       0, None, LpInteger)
    
    prob += lpSum(y[j] for j in range(max_barras))
    
    for i in range(len(articulos)):
        prob += lpSum(x[(i, j)] for j in range(max_barras)) >= articulos[i]['quantity']
        
    for j in range(max_barras):
        prob += lpSum(x[(i, j)] * articulos[i]['length'] 
                   for i in range(len(articulos))) <= largo_material * y[j]
    
    start_time = time.time()
    prob.solve(PULP_CBC_CMD(msg=0))
    tiempo_ejecucion = time.time() - start_time
    
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
    
    barras.sort(key=lambda x: x['desperdicio'])
    
    return {
        "tiempo_ejecucion": round(tiempo_ejecucion, 2),
        "total_barras": len(barras),
        "barras": barras
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
