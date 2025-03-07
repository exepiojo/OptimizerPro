from flask import Blueprint, request, jsonify, render_template
from .utils import calcular_optimizacion

optimization_bp = Blueprint('optimization', __name__)

# Ruta para la página de optimización
@optimization_bp.route('/optimization')
def optimization_page():
    return render_template('optimization.html')

# Ruta para la API de optimización
@optimization_bp.route('/optimize', methods=['POST'])
def optimize():
    data = request.json
    result = calcular_optimizacion(data)
    return jsonify(result)