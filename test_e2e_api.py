import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("Iniciando bateria de pruebas E2E contra", BASE_URL)
    
    # 1. Healthcheck
    try:
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print("✅ Healthcheck OK")
    except Exception as e:
        print("❌ Healthcheck Falló:", e)
    
    # 2. CORS Test
    try:
        headers = {"Origin": "http://evil.com"}
        r_cors = requests.options(f"{BASE_URL}/predict-today", headers=headers)
        if "access-control-allow-origin" in r_cors.headers:
            acao = r_cors.headers["access-control-allow-origin"]
            if acao == "*":
                print("⚠️ CORS está abierto a cualquier dominio (CORS: *)")
            else:
                print(f"✅ CORS restringe a dominios específicos: {acao}")
        else:
            print("✅ CORS no permite Origins arbitrarios explícitamente")
    except Exception as e:
        print("⚠️ Error en Test CORS:", e)
        
    # 3. Datos NBA
    try:
        r_nba = requests.get(f"{BASE_URL}/predict-today")
        assert r_nba.status_code == 200
        nba_data = r_nba.json()
        assert "predictions" in nba_data
        print(f"✅ API NBA retorna predicciones completas: {len(nba_data['predictions'])} juegos.")
    except Exception as e:
        print("❌ API NBA Falló:", e)
    
    # 4. Datos Football
    try:
        r_ftb = requests.get(f"{BASE_URL}/predict-football")
        assert r_ftb.status_code == 200
        ftb_data = r_ftb.json()
        assert "predictions" in ftb_data
        print(f"✅ API Fútbol retorna predicciones completas: {len(ftb_data['predictions'])} juegos.")
    except Exception as e:
        print("❌ API Fútbol Falló:", e)
    
    # 5. Injection Simulation / Pydantic validation
    try:
        r_sqli = requests.get(f"{BASE_URL}/history/full?days=1 OR 1=1")
        assert r_sqli.status_code in [422, 400], f"Falta validación estricta de tipos. Retornó: {r_sqli.status_code}"
        print("✅ Defensa contra inyecciones vía Pydantic operando (Bloqueó string sucio en parámetro Int)")
    except AssertionError as e:
        print("⚠️ Alerta SQLi/Type:", e)
    except Exception as e:
        print("⚠️ Error probando SQLi:", e)

if __name__ == "__main__":
    run_tests()
