import requests
import json

BASE_URL = "http://localhost:8000"

print("🔍 NBA Vibecoding AI - Test Suite\n")
print("=" * 50)

# Test 1: Endpoint principal
print("\n✅ Test 1: GET /pronosticos-hoy")
try:
    response = requests.get(f"{BASE_URL}/pronosticos-hoy", timeout=15)
    data = response.json()
    
    if response.status_code == 200:
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Predicciones: {len(data.get('predictions', []))}")
        
        # Verificar primera predicción
        if data['predictions']:
            pred = data['predictions'][0]
            print(f"   ✓ Primera predicción: {pred['home_team']} vs {pred['away_team']}")
            print(f"   ✓ EV Value: {pred.get('ev_value', 'N/A')}%")
            print(f"   ✓ Kelly Stake: {pred.get('kelly_stake_pct', 'N/A')}%")
            print(f"   ✓ Warning Level: {pred.get('warning_level', 'N/A')}")
    else:
        print(f"   ✗ Error: Status {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")

# Test 2: Performance stats
print("\n✅ Test 2: GET /performance-stats")
try:
    response = requests.get(f"{BASE_URL}/performance-stats?days=30", timeout=5)
    data = response.json()
    
    if response.status_code == 200:
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Total Bets: {data.get('total_bets', 0)}")
        print(f"   ✓ Win Rate: {data.get('win_rate', 0)}%")
        print(f"   ✓ ROI: {data.get('roi', 0)}%")
    else:
        print(f"   ✗ Error: Status {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")

# Test 3: Live games
print("\n✅ Test 3: GET /live-games")
try:
    response = requests.get(f"{BASE_URL}/live-games", timeout=5)
    data = response.json()
    
    if response.status_code == 200:
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Status: {data.get('status', 'N/A')}")
        print(f"   ✓ Live Games: {len(data.get('live_games', []))}")
    else:
        print(f"   ✗ Error: Status {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")

# Test 4: History
print("\n✅ Test 4: GET /history")
try:
    response = requests.get(f"{BASE_URL}/history?days=7", timeout=5)
    data = response.json()
    
    if response.status_code == 200:
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Predictions in history: {len(data.get('predictions', []))}")
    else:
        print(f"   ✗ Error: Status {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")

# Test 5: Frontend
print("\n✅ Test 5: GET / (Frontend)")
try:
    response = requests.get(BASE_URL, timeout=5)
    
    if response.status_code == 200:
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ HTML Size: {len(response.text)} bytes")
        
        # Verificar elementos clave
        html = response.text
        checks = [
            ("Predicciones button", "btn-predictions" in html),
            ("Bankroll button", "btn-bankroll" in html),
            ("Chart.js", "chart.js" in html),
            ("NBA Logos dict", "NBA_LOGOS" in html),
        ]
        
        for name, result in checks:
            print(f"   {'✓' if result else '✗'} {name}: {'OK' if result else 'Not found'}")
    else:
        print(f"   ✗ Error: Status {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")

print("\n" + "=" * 50)
print("🎉 Tests completados")
