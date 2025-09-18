import pytest
from app import app
from app import (
    get_deudas, get_saldo, realizar_pago, cancelar_pago,
    oauth_token, deudas_data, saldo_data, pagos
)
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Resetear los datos para cada test para asegurar la independencia
        deudas_data.clear()
        deudas_data.update({
            '12345': [{"monto": 100, "mes": "Mayo"}, {"monto": 150, "mes": "Junio"}],
            '1425': [{"monto": 250, "mes": "Julio"}]
        })
        saldo_data.clear()
        saldo_data.update({'12345': 200, '1425': 500})
        pagos.clear()
        yield client

def get_token(client):
    """Función auxiliar para obtener un token de autenticación."""
    response = client.post('/oauth/token')
    return response.get_json()['token']

## Test 1: Generar OAuth Token
def test_1_oauth_token_generation(client):
    response = client.post('/oauth/token')
    data = response.get_json()
    assert response.status_code == 200
    assert 'token' in data
    assert 'created_at' in data
    assert 'expires_at' in data
    assert 'id' in data

## Test 2: Obtener Deudas
def test_2_get_deudas_success(client):
    """Test para consultar deudas con un identificador válido y el formato correcto."""
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/deudas?codigo=ci@12345', headers=headers)
    assert response.status_code == 200
    assert "deudas" in response.get_json()
    assert len(response.get_json()["deudas"]) > 0

## Test 3: Obtener Saldo
def test_3_get_saldo_success(client):
    """Test para consultar el saldo con un token válido."""
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/saldo', headers=headers)
    assert response.status_code == 200
    assert "saldo" in response.get_json()

## Test 4: Pago Exitoso
def test_4_realizar_pago_success(client):
    """Test para realizar un pago exitoso cuando el saldo es suficiente."""
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    response_pago = client.post('/pagar?codigo=ci@12345', headers=headers)
    assert response_pago.status_code == 200
    assert "pago_id" in response_pago.get_json()
    assert response_pago.get_json()["mensaje"] == "Pago realizado con éxito."
    assert saldo_data['12345'] == 100 # Saldo inicial 200 - deuda 100

## Test 5: Pago con Fondos Insuficientes
def test_5_realizar_pago_insufficient_funds(client):
    """Test para verificar que el pago falla con un mensaje de error si el saldo es insuficiente."""
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    # Forzar un saldo bajo para el test
    saldo_data['12345'] = 50
    # La URL ha cambiado para usar 'codigo'
    response_pago = client.post('/pagar?codigo=ci@12345', headers=headers)
    assert response_pago.status_code == 400
    assert response_pago.get_json()["error"] == "Saldo insuficiente para cubrir la deuda."

## Test 6: Cancelar Pago dentro del Límite de Tiempo
def test_6_cancelar_pago_within_time_limit(client):
    """Test para cancelar un pago dentro del límite de 5 minutos."""
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    # Realizar el pago 
    response_pago = client.post('/pagar?codigo=ci@12345', headers=headers)
    pago_id = response_pago.get_json()['pago_id']
    # Cancelar el pago
    response_cancelacion = client.delete(f'/cancelar/{pago_id}?codigo=ci@12345', headers=headers)
    assert response_cancelacion.status_code == 200
    assert response_cancelacion.get_json()["mensaje"] == "Pago cancelado exitosamente."
    assert len(deudas_data['12345']) == 2 # La deuda debe ser devuelta
    assert saldo_data['12345'] == 200 # El saldo debe ser restaurado