from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
from io import BytesIO
import os
from sqlalchemy.exc import IntegrityError 

# Configuración inicial
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///produccion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
db = SQLAlchemy(app)

# Modelo de base de datos
class Produccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    implemento = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    chasis = db.Column(db.String(50), unique=True, nullable=False)
    avance = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'fecha': self.fecha.strftime('%Y-%m-%d'),
            'implemento': self.implemento,
            'modelo': self.modelo,
            'chasis': self.chasis,
            'avance': self.avance
        }

# Inicialización de la base de datos
with app.app_context():
    db.create_all()
    os.makedirs('instance', exist_ok=True)

# Rutas principales
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/optimizacion.html')
def optimizacion():
    return render_template('optimizacion.html')

@app.route('/conversion.html')
def conversion():
    return render_template('conversion.html')

@app.route('/dashboard.html')
def dashboard():
    return render_template('dashboard.html')

# API CRUD
@app.route('/api/produccion', methods=['GET', 'POST'])  # Agregar método GET
def gestion_produccion():
    try:
        if request.method == 'GET':
            registros = Produccion.query.order_by(Produccion.fecha.desc()).all()
            return jsonify([r.to_dict() for r in registros]), 200
        data = request.get_json()
        
        # Validación básica de campos
        required_fields = ['fecha', 'implemento', 'modelo', 'chasis', 'avance']
        if not all(key in data for key in required_fields):
            return jsonify({'error': f'Campos requeridos faltantes: {required_fields}'}), 400
        
        # Validación de implemento y modelo
        valido, mensaje_error = validar_implemento(data['implemento'], data['modelo'])
        if not valido:
            return jsonify({'error': mensaje_error}), 400
        
        # Validación de avance
        if not 0 <= int(data['avance']) <= 100:
            return jsonify({'error': 'El avance debe estar entre 0 y 100'}), 400
        
        # Validación de fecha
        try:
            fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        # Crear registro
        nuevo_registro = Produccion(
            fecha=fecha,
            implemento=data['implemento'].upper(),
            modelo=data['modelo'].upper(),
            chasis=data['chasis'],
            avance=int(data['avance'])
        )
        
        db.session.add(nuevo_registro)
        db.session.commit()
        return jsonify(nuevo_registro.to_dict()), 201
    
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'El número de chasis ya existe'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

    # Constantes de validación
IMPLEMENTOS_VALIDOS = {
    'TOLVA': ['14TN', '16TN', '22TN', '24TN', '26TN', '28TN', '28=>30TN', 
              '30(4)TN', '30(6)TN', '33(4)TN', '33(6)TN'],
    'MIXER': ['1600', '2600'],
    'EMBOLSADORAS': ['EVO']
}

def validar_implemento(implemento, modelo):
    """Valida que el implemento y modelo sean correctos"""
    if implemento.upper() not in IMPLEMENTOS_VALIDOS:
        return False, f"Implemento no válido. Opciones: {list(IMPLEMENTOS_VALIDOS.keys())}"
    
    modelos_validos = IMPLEMENTOS_VALIDOS[implemento.upper()]
    if modelo.upper() not in [m.upper() for m in modelos_validos]:
        return False, f"Modelo no válido para {implemento}. Opciones: {modelos_validos}"
    
    return True, None


@app.route('/api/produccion/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def gestion_registro(id):
    try:
        registro = Produccion.query.get_or_404(id)
        
        if request.method == 'GET':
            return jsonify(registro.to_dict())
        
        if request.method == 'PUT':
            data = request.get_json()
            
            if 'fecha' in data:
                registro.fecha = datetime.strptime(data['fecha'], '%Y-%m-%d')
            if 'implemento' in data:
                registro.implemento = data['implemento']
            if 'modelo' in data:
                registro.modelo = data['modelo']
            if 'chasis' in data:
                registro.chasis = data['chasis']
            if 'avance' in data:
                registro.avance = data['avance']
            
            db.session.commit()
            return jsonify(registro.to_dict())
        
        if request.method == 'DELETE':
            db.session.delete(registro)
            db.session.commit()
            return jsonify({'mensaje': 'Registro eliminado'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Manejo de errores
@app.errorhandler(404)
def pagina_no_encontrada(error):
    return jsonify({'error': 'Recurso no encontrado'}), 404

@app.errorhandler(500)
def error_servidor(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/cargar-excel', methods=['POST'])
def cargar_excel():
    try:
        if 'file' not in request.files:
            print("Error: No se encontró el archivo en la solicitud")  # Debug
            return jsonify({'error': 'No se encontró el archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            print("Error: Archivo no seleccionado")  # Debug
            return jsonify({'error': 'Archivo no seleccionado'}), 400
        
        if not file.filename.endswith('.xlsx'):
            print("Error: El archivo no es un .xlsx")  # Debug
            return jsonify({'error': 'Solo se permiten archivos .xlsx'}), 400
        
        print(f"Archivo recibido: {file.filename}")  # Debug

        # Leer el archivo Excel
        excel_data = file.read()
        df = pd.read_excel(BytesIO(excel_data))

        # Validar columnas
        required_columns = ['Fecha', 'Implementos', 'Modelo', 'N° CHASIS', 'Avance']
        if not all(col in df.columns for col in required_columns):
            print(f"Error: Columnas faltantes. Esperadas: {required_columns}, Encontradas: {df.columns.tolist()}")  # Debug
            return jsonify({'error': f'Columnas requeridas faltantes: {required_columns}'}), 400
        
        print("Columnas válidas encontradas")  # Debug

        registros_exitosos = 0
        errores = []
        
        for index, row in df.iterrows():
            try:
                # Convertir fecha
                fecha = pd.to_datetime(row['Fecha']).date()
                
                nuevo_registro = Produccion(
                    fecha=fecha,
                    implemento=str(row['Implementos']),
                    modelo=str(row['Modelo']),
                    chasis=str(row['N° CHASIS']),
                    avance=int(row['Avance'])
                )
                db.session.add(nuevo_registro)
                db.session.commit()
                registros_exitosos += 1
            except Exception as e:
                db.session.rollback()
                errores.append(f"Fila {index + 2}: {str(e)}")
                print(f"Error en fila {index + 2}: {str(e)}")  # Debug
        
        mensaje = f"{registros_exitosos} registros cargados exitosamente"
        if errores:
            mensaje += f". Errores: {', '.join(errores)}"
        
        return jsonify({'mensaje': mensaje}), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en el servidor: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500
    
# Agregar después de la ruta /api/cargar-excel
@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    implemento = request.args.get('implemento')
    año = request.args.get('año')

    query = db.session.query(
        db.func.strftime('%Y', Produccion.fecha).label('año'),
        db.func.strftime('%m', Produccion.fecha).label('mes'),
        Produccion.implemento,
        db.func.count().label('cantidad')
    )

    if implemento and implemento != 'TODOS':
        query = query.filter(Produccion.implemento == implemento)
    if año and año != 'TODOS':
        query = query.filter(db.func.strftime('%Y', Produccion.fecha) == año)

    datos = query.group_by('año', 'mes', 'implemento').all()

    resultado = []
    for d in datos:
        resultado.append({
            'año': d.año,
            'mes': d.mes,
            'implemento': d.implemento,
            'cantidad': d.cantidad
        })
    
    return jsonify(resultado)

@app.route('/api/filtros', methods=['GET'])
def obtener_filtros():
    años = db.session.query(
        db.func.strftime('%Y', Produccion.fecha).label('año')
    ).distinct().all()
    
    implementos = db.session.query(
        Produccion.implemento
    ).distinct().all()

    return jsonify({
        'años': [a[0] for a in años],
        'implementos': [i[0] for i in implementos]
    })

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        material_length = data['materialLength']
        saw_kerf = data['sawKerf']
        articles = sorted(data['articles'], key=lambda x: (-x['length'], -x['quantity']))
        
        bars = []
        remaining = [{'name': a['name'], 
                      'length': a['length'], 
                      'quantity': a['quantity']} for a in articles]

        while any(item['quantity'] > 0 for item in remaining):
            current_bar = []
            used_length = 0
            current_kerf = 0
            
            # Primera pasada: artículos completos
            for item in remaining:
                if item['quantity'] <= 0:
                    continue
                
                max_posible = (material_length - used_length - current_kerf) // item['length']
                if max_posible > 0:
                    actual_qty = min(max_posible, item['quantity'])
                    
                    current_bar.extend([{'name': item['name'], 'length': item['length']}] * actual_qty)
                    used_length += item['length'] * actual_qty
                    current_kerf += saw_kerf * (actual_qty - 1)  # Kerf entre piezas
                    item['quantity'] -= actual_qty

            # Segunda pasada: intentar llenar espacios
            if current_bar:
                # Ajustar kerf final (el último corte no cuenta)
                total_kerf = saw_kerf * (len(current_bar) - 1)
                remaining_length = material_length - (used_length + total_kerf)
                
                # Buscar piezas que quepan en el espacio restante
                for item in remaining:
                    if item['quantity'] > 0 and item['length'] <= remaining_length:
                        current_bar.append({'name': item['name'], 'length': item['length']})
                        item['quantity'] -= 1
                        used_length += item['length']
                        remaining_length -= item['length']
                        break
                
                bars.append({
                    'items': current_bar,
                    'waste': material_length - (used_length + total_kerf)
                })

        return jsonify({'bars': bars}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)