from flask import Flask, request, jsonify, render_template
from pulp import *
import matplotlib
matplotlib.use('Agg')
import traceback
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        
        # Validación de datos
        required_fields = ['materialLength', 'articles']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Datos incompletos"}), 400
            
        result = calcular_optimizacion(data)
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
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
    
    # Restricciones
    for i in range(len(articulos)):
        prob += lpSum(x[(i, j)] for j in range(max_barras)) >= articulos[i]['quantity']
        
    for j in range(max_barras):
        prob += lpSum(x[(i, j)] * articulos[i]['length'] 
                   for i in range(len(articulos))) <= largo_material * y[j]
    
    prob.solve()
    
    barras = []
    if LpStatus[prob.status] == "Optimal":
        for j in range(max_barras):
            if value(y[j]) == 1:
                detalle = []
                total = 0
                for i in range(len(articulos)):
                    cantidad = value(x[(i, j)])
                    if cantidad > 0:
                        detalle.extend([
                            {
                                "name": articulos[i]['name'],
                                "length": articulos[i]['length']
                            } for _ in range(int(cantidad))
                        ])
                        total += articulos[i]['length'] * cantidad
                barras.append({
                    "id": str(j+1),
                    "total": total,
                    "waste": largo_material - total,
                    "items": detalle
                })
    
    return {
        "status": LpStatus[prob.status],
        "bars": sorted(barras, key=lambda x: x['waste'])
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
