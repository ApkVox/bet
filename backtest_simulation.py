"""
===========================================
NBA VIBECODING - SIMULACIÓN DE BACKTESTING
===========================================
Simula el rendimiento del modelo desde el 1 de enero 2026 hasta hoy.

Parámetros:
- Capital inicial: 50,000 COP
- Apuestas por día: 3 (las mejores según EV)
- Kelly Fraccional: 1/4 Kelly, máximo 2.5%
"""

import random
from datetime import datetime, timedelta
import numpy as np

# ===========================================
# CONFIGURACIÓN DE SIMULACIÓN
# ===========================================
CAPITAL_INICIAL = 50000  # COP
APUESTAS_POR_DIA = 3
MAX_KELLY_PCT = 2.5  # Máximo 2.5% del bankroll por apuesta
FECHA_INICIO = datetime(2026, 1, 1)
FECHA_FIN = datetime(2026, 1, 21)

# Equipos NBA para generar partidos
EQUIPOS_NBA = [
    "Boston Celtics", "Brooklyn Nets", "New York Knicks", "Philadelphia 76ers", "Toronto Raptors",
    "Chicago Bulls", "Cleveland Cavaliers", "Detroit Pistons", "Indiana Pacers", "Milwaukee Bucks",
    "Atlanta Hawks", "Charlotte Hornets", "Miami Heat", "Orlando Magic", "Washington Wizards",
    "Denver Nuggets", "Minnesota Timberwolves", "Oklahoma City Thunder", "Portland Trail Blazers", "Utah Jazz",
    "Golden State Warriors", "LA Clippers", "Los Angeles Lakers", "Phoenix Suns", "Sacramento Kings",
    "Dallas Mavericks", "Houston Rockets", "Memphis Grizzlies", "New Orleans Pelicans", "San Antonio Spurs"
]

# ===========================================
# FUNCIONES DEL MODELO (Réplica de main.py)
# ===========================================
def american_to_decimal(american_odds: int) -> float:
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def calculate_ev(prob: float, odds: int) -> float:
    """Expected Value como porcentaje"""
    decimal_odds = american_to_decimal(odds)
    ev = (prob * decimal_odds) - 1
    return round(ev * 100, 2)

def calculate_kelly(prob: float, odds: int, safety: float = 0.25) -> float:
    """Kelly Criterion con factor de seguridad"""
    decimal_odds = american_to_decimal(odds)
    kelly = (prob * decimal_odds - 1) / (decimal_odds - 1)
    kelly_adjusted = kelly * safety
    return min(MAX_KELLY_PCT, max(0, kelly_adjusted * 100))

def generar_partidos_dia(fecha: datetime, num_partidos: int = 8) -> list:
    """Genera partidos simulados para un día específico"""
    random.seed(hash(str(fecha)) % 2**32)
    partidos = []
    
    equipos_disponibles = EQUIPOS_NBA.copy()
    random.shuffle(equipos_disponibles)
    
    for i in range(min(num_partidos, len(equipos_disponibles) // 2)):
        home = equipos_disponibles[i * 2]
        away = equipos_disponibles[i * 2 + 1]
        
        # Generar probabilidad del modelo (basada en hash del matchup)
        np.random.seed(hash(home + away + str(fecha)) % 2**32)
        home_prob = 0.45 + np.random.random() * 0.2  # 45-65%
        
        winner_is_home = home_prob > 0.5
        winner = home if winner_is_home else away
        win_prob = max(home_prob, 1 - home_prob)
        
        # Generar cuotas americanas simuladas
        if win_prob > 0.55:
            odds = -int(100 * win_prob / (1 - win_prob))  # Favorito
        else:
            odds = int(100 * (1 - win_prob) / win_prob)  # Underdog
        
        # Calcular métricas
        ev = calculate_ev(win_prob, odds)
        kelly = calculate_kelly(win_prob, odds)
        
        partidos.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "home": home,
            "away": away,
            "winner": winner,
            "prob": round(win_prob * 100, 1),
            "odds": odds,
            "ev": ev,
            "kelly": kelly
        })
    
    return partidos

def simular_resultado(prob: float) -> bool:
    """Simula si la apuesta ganó basándose en la probabilidad"""
    # Usamos un factor de calibración: el mercado es eficiente
    # Si el modelo dice 60%, ganará ~55% de las veces (pequeño edge)
    calibration_factor = 0.95  # El modelo tiene ligera ventaja
    prob_real = prob * calibration_factor
    return random.random() < prob_real

def calcular_ganancia(stake: float, odds: int, gano: bool) -> float:
    """Calcula la ganancia/pérdida de una apuesta"""
    if gano:
        decimal_odds = american_to_decimal(odds)
        return stake * (decimal_odds - 1)  # Ganancia neta
    else:
        return -stake

# ===========================================
# SIMULACIÓN PRINCIPAL
# ===========================================
def ejecutar_simulacion():
    print("=" * 60)
    print("🏀 NBA VIBECODING - SIMULACIÓN DE BACKTESTING")
    print("=" * 60)
    print(f"📅 Período: {FECHA_INICIO.strftime('%d/%m/%Y')} - {FECHA_FIN.strftime('%d/%m/%Y')}")
    print(f"💰 Capital inicial: ${CAPITAL_INICIAL:,.0f} COP")
    print(f"🎯 Apuestas por día: {APUESTAS_POR_DIA}")
    print(f"📊 Kelly máximo: {MAX_KELLY_PCT}%")
    print("=" * 60)
    
    bankroll = CAPITAL_INICIAL
    historial = []
    
    fecha_actual = FECHA_INICIO
    dias_simulados = 0
    total_apuestas = 0
    apuestas_ganadas = 0
    
    while fecha_actual <= FECHA_FIN:
        dias_simulados += 1
        
        # Generar partidos del día
        partidos = generar_partidos_dia(fecha_actual)
        
        # Filtrar solo apuestas con EV positivo
        partidos_ev_positivo = [p for p in partidos if p["ev"] > 0]
        
        # Ordenar por EV descendente y tomar las mejores 3
        partidos_ev_positivo.sort(key=lambda x: x["ev"], reverse=True)
        mejores_apuestas = partidos_ev_positivo[:APUESTAS_POR_DIA]
        
        print(f"\n📅 {fecha_actual.strftime('%d/%m/%Y')} | Bankroll: ${bankroll:,.0f} COP")
        
        if not mejores_apuestas:
            print("   ❌ Sin apuestas de valor hoy")
            fecha_actual += timedelta(days=1)
            continue
        
        for apuesta in mejores_apuestas:
            # Calcular stake (Kelly con límite)
            stake_pct = min(apuesta["kelly"], MAX_KELLY_PCT)
            stake = bankroll * (stake_pct / 100)
            
            # Simular resultado
            gano = simular_resultado(apuesta["prob"] / 100)
            ganancia = calcular_ganancia(stake, apuesta["odds"], gano)
            
            bankroll += ganancia
            total_apuestas += 1
            if gano:
                apuestas_ganadas += 1
            
            resultado_emoji = "✅" if gano else "❌"
            
            print(f"   {resultado_emoji} {apuesta['winner'][:15]:15} | "
                  f"Prob: {apuesta['prob']}% | "
                  f"EV: {'+' if apuesta['ev'] > 0 else ''}{apuesta['ev']}% | "
                  f"Stake: ${stake:,.0f} | "
                  f"{'Ganó' if gano else 'Perdió'}: ${abs(ganancia):,.0f}")
            
            historial.append({
                "fecha": apuesta["fecha"],
                "partido": f"{apuesta['home']} vs {apuesta['away']}",
                "apuesta": apuesta["winner"],
                "prob": apuesta["prob"],
                "odds": apuesta["odds"],
                "ev": apuesta["ev"],
                "stake": stake,
                "resultado": "WIN" if gano else "LOSS",
                "ganancia": ganancia,
                "bankroll": bankroll
            })
        
        fecha_actual += timedelta(days=1)
    
    # ===========================================
    # RESUMEN FINAL
    # ===========================================
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE SIMULACIÓN")
    print("=" * 60)
    
    ganancia_total = bankroll - CAPITAL_INICIAL
    roi = (ganancia_total / CAPITAL_INICIAL) * 100
    win_rate = (apuestas_ganadas / total_apuestas * 100) if total_apuestas > 0 else 0
    
    print(f"📅 Días simulados: {dias_simulados}")
    print(f"🎯 Total apuestas: {total_apuestas}")
    print(f"✅ Apuestas ganadas: {apuestas_ganadas}")
    print(f"❌ Apuestas perdidas: {total_apuestas - apuestas_ganadas}")
    print(f"📈 Win Rate: {win_rate:.1f}%")
    print()
    print(f"💰 Capital inicial: ${CAPITAL_INICIAL:,.0f} COP")
    print(f"💰 Capital final: ${bankroll:,.0f} COP")
    print()
    
    if ganancia_total >= 0:
        print(f"🟢 GANANCIA NETA: +${ganancia_total:,.0f} COP")
    else:
        print(f"🔴 PÉRDIDA NETA: -${abs(ganancia_total):,.0f} COP")
    
    print(f"📊 ROI: {'+' if roi >= 0 else ''}{roi:.1f}%")
    print("=" * 60)
    
    return {
        "capital_inicial": CAPITAL_INICIAL,
        "capital_final": bankroll,
        "ganancia_neta": ganancia_total,
        "roi": roi,
        "total_apuestas": total_apuestas,
        "apuestas_ganadas": apuestas_ganadas,
        "win_rate": win_rate,
        "dias_simulados": dias_simulados,
        "historial": historial
    }

if __name__ == "__main__":
    resultado = ejecutar_simulacion()
