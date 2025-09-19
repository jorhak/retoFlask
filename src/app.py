from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid
from flask_cors import CORS

# Inicialización de la aplicación
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todos los dominios

# Simulación de una base de datos en memoria
usuarios = {}
pagos = {}
deudas_data = {
    '12345': [{"monto": 100, "mes": "Mayo"}, {"monto": 150, "mes": "Junio"}],
    '1425': [{"monto": 250, "mes": "Julio"}]
}
saldo_data = {'12345': 500, '1425': 500}

# Decorador para la autenticación OAuth
def require_oauth_token(f):
    # ... (mismo código) ...
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Token de autenticación es requerido."}), 401
        
        token = auth_header.split(' ')[1]
        
        if token not in usuarios or datetime.fromisoformat(usuarios[token]['expires_at']) < datetime.now():
            return jsonify({"error": "Token inválido o expirado."}), 401
            
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Nueva función para parsear los parámetros personalizados
def parse_custom_params(param_string):
    """
    Parsea una cadena con el formato 'key@value$key@value'.
    Retorna un diccionario de los parámetros.
    """
    parsed = {}
    if not param_string:
        return parsed
        
    parts = param_string.split('$')
    for part in parts:
        key_value = part.split('@')
        if len(key_value) == 2:
            key, value = key_value
            parsed[key] = value
        else:
            # Puedes manejar este error de forma más robusta si lo deseas
            return None
    return parsed

# Endpoint para la generación de token OAuth
@app.route('/oauth/token', methods=['POST'])
def oauth_token():
    # ... (mismo código) ...
    token = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=30)
    
    user_id = str(uuid.uuid4())
    usuarios[token] = {
        'token': token,
        'created_at': created_at.isoformat(),
        'expires_at': expires_at.isoformat(),
        'id': user_id
    }
    
    return jsonify(usuarios[token]), 200

# Endpoint para consultar deudas
@app.route('/deudas', methods=['GET'])
@require_oauth_token
def get_deudas():
    # Accede al parámetro 'codigo' del query string
    param_string = request.args.get('codigo')
    params = parse_custom_params(param_string)
    
    if not params:
        return jsonify({"error": "Formato de parámetros de URL inválido o no proporcionado."}), 400
        
    deudas_encontradas = []
    
    for key, value in params.items():
        if value in deudas_data:
            deudas_encontradas.extend(deudas_data[value])
            
    if not deudas_encontradas:
        return jsonify({"mensaje": "No se encontraron deudas para los identificadores proporcionados."}), 404
    
    return jsonify({"deudas": deudas_encontradas}), 200

# Endpoint para consultar saldo
@app.route('/saldo', methods=['GET'])
@require_oauth_token
def get_saldo():
    # ... (mismo código, sin cambios ya que no usa parámetros de esta manera) ...
    identificador_usuario = '12345'
    saldo_actual = saldo_data.get(identificador_usuario)

    if saldo_actual is None:
        return jsonify({"error": "Saldo no disponible para este usuario."}), 404
    
    return jsonify({"saldo": saldo_actual}), 200

# Endpoint para realizar el pago
@app.route('/pagar', methods=['POST'])
@require_oauth_token
def realizar_pago():
    # Accede al parámetro 'codigo' para obtener el identificador
    param_string = request.args.get('codigo')
    params = parse_custom_params(param_string)
    
    if not params or not 'ci' in params:
        return jsonify({"error": "El identificador del cliente (ci) es requerido para el pago."}), 400
    
    identificador_usuario = params['ci']
    
    saldo_actual = saldo_data.get(identificador_usuario, 0)
    deudas_usuario = deudas_data.get(identificador_usuario, [])
    
    if not deudas_usuario:
        return jsonify({"error": "No tienes deudas pendientes."}), 400
        
    primera_deuda = deudas_usuario[0]
    monto_deuda = primera_deuda['monto']
    print("Saldo actual:", saldo_actual, "Monto deuda:", monto_deuda)
    if saldo_actual < monto_deuda:
        return jsonify({"error": "Saldo insuficiente para cubrir la deuda."}), 400
    else:
        pago_id = str(uuid.uuid4())
        pagos[pago_id] = {
            'monto': monto_deuda,
            'deuda_pagada': primera_deuda,
            'timestamp': datetime.now(),
            'ci': identificador_usuario
        }
        
        saldo_data[identificador_usuario] -= monto_deuda
        deudas_data[identificador_usuario].pop(0)
        
        return jsonify({
            "pago_id": pago_id,
            "mensaje": "Pago realizado con éxito.",
            "saldo_restante": saldo_data[identificador_usuario]
        }), 200

# Endpoint para cancelar el pago
@app.route('/cancelar/<pago_id>', methods=['DELETE'])
@require_oauth_token
def cancelar_pago(pago_id):
    if pago_id not in pagos:
        return jsonify({"error": "ID de pago no encontrado."}), 404
    
    param_string = request.args.get('codigo')
    params = parse_custom_params(param_string)

    if not params or not 'ci' in params:
        return jsonify({"error": "El identificador del cliente (ci) es requerido para cancelar el pago."}), 400

    pago = pagos[pago_id]
    identificador_usuario = params['ci']
    
    if identificador_usuario != pago['ci']:
        return jsonify({"error": "El pago no corresponde al identificador de cliente proporcionado."}), 403

    tiempo_transcurrido = datetime.now() - pago['timestamp']
    
    if tiempo_transcurrido > timedelta(minutes=5):
        return jsonify({"error": "El tiempo límite de 5 minutos para cancelar el pago ha expirado."}), 400
        
    saldo_data[identificador_usuario] += pago['monto']
    deudas_data[identificador_usuario].insert(0, pago['deuda_pagada'])
    del pagos[pago_id]
    
    return jsonify({"mensaje": "Pago cancelado exitosamente."}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)