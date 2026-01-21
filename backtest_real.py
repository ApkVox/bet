# -*- coding: utf-8 -*-
"""
NBA VIBECODING - BACKTESTING "TOTAL WAR" (50% STAKE)
Inluye: Moneyline, Spread y Over/Under.
Estrategia: Portfolio completo con 50% de riesgo diario.
"""

import requests
import json
import os
from datetime import datetime, timedelta
import numpy as np
import time
import sys
import random

# Fix encoding para Windows
sys.stdout.reconfigure(encoding='utf-8')

# CONFIGURACION TOTAL WAR
CAPITAL_INICIAL = 5000            # COP
APUESTAS_POR_DIA = 3
PORCENTAJE_APUESTA_DIARIO = 0.50   # 50% Riesgo Diario
FECHA_INICIO = datetime(2026, 1, 1)
FECHA_FIN = datetime(2026, 1, 20)
ARCHIVO_CACHE = "nba_results_cache.json"

def american_to_decimal(american_odds):
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def calculate_ev(prob_pct, odds):
    decimal_odds = american_to_decimal(odds)
    ev = ((prob_pct/100) * decimal_odds) - 1
    return round(ev * 100, 2)

# Sistema de Caché
def cargar_cache():
    if os.path.exists(ARCHIVO_CACHE):
        with open(ARCHIVO_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_cache(cache):
    with open(ARCHIVO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

RESULTS_CACHE = cargar_cache()

def obtener_partidos_nba(fecha):
    fecha_str = fecha.strftime("%Y%m%d")
    if fecha_str in RESULTS_CACHE:
        return RESULTS_CACHE[fecha_str]
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={fecha_str}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        partidos = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            if len(competitors) < 2: continue
            
            home_team = None
            away_team = None
            home_score = 0
            away_score = 0
            
            for comp in competitors:
                team_name = comp.get("team", {}).get("displayName", "Unknown")
                score = int(comp.get("score", 0) or 0)
                if comp.get("homeAway") == "home":
                    home_team = team_name
                    home_score = score
                else:
                    away_team = team_name
                    away_score = score
            
            if home_team and away_team:
                if home_score > away_score: winner_real = home_team
                elif away_score > home_score: winner_real = away_team
                else: winner_real = None
                
                status = competition.get("status", {}).get("type", {}).get("name", "")
                if status == "STATUS_FINAL" and winner_real:
                    partidos.append({
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "home": home_team,
                        "away": away_team,
                        "home_score": home_score,
                        "away_score": away_score,
                        "winner_real": winner_real
                    })
        
        if partidos:
            RESULTS_CACHE[fecha_str] = partidos
            guardar_cache(RESULTS_CACHE)
        return partidos
    except Exception as e:
        print(f"   [!] Error API: {str(e)[:40]}")
        return []

def simular_mercados_secundarios(partido, seed_val):
    """
    Simula líneas de mercado (Spread y O/U) basadas en el resultado real + ruido.
    Esto simula un mercado eficiente difícil de batir.
    """
    np.random.seed(seed_val)
    
    real_total = partido["home_score"] + partido["away_score"]
    real_diff = partido["home_score"] - partido["away_score"]  # Positivo = Home gana por X
    
    # 1. Simular Línea O/U (Real Total +/- 8 puntos random)
    # Mercado no sabe el futuro, pero es muy bueno prediciendo
    market_ou_bias = np.random.normal(0, 5) 
    market_ou_line = round(real_total + market_ou_bias - 0.5) + 0.5 # .5 para no empates
    
    # 2. Simular Spread (Real Diff +/- 6 puntos random)
    market_spread_bias = np.random.normal(0, 4)
    # Si Home ganó por 10, spread mercado tal vez era -8.5 o -12.5
    market_spread_line = round(real_diff + market_spread_bias - 0.5) + 0.5
    # Spread se expresa para el Home: -5.5 significa Home favorito por 5.5
    # Si market_spread_line es positivo (ej 7.5), significa que mercado esperaba que Home ganara por 7.5
    # Entonces el spread es Home -7.5
    
    return {
        "ou_line": market_ou_line,
        "spread_line": market_spread_line, # Positivo = Home Favorito, Negativo = Away Favorito en margen
        "real_total": real_total,
        "real_diff": real_diff
    }

def generar_predicciones_multiples(partido, mercados, fecha):
    """Genera ONE PARLAY prediction (ML + O/U)"""
    seed_val = hash(partido["home"] + partido["away"] + str(fecha)) % 2**32
    np.random.seed(seed_val)
    preds = []
    
    # --- 1. MONEYLINE LEG ---
    model_prob_ml = 0.55 + (np.random.random() - 0.5) * 0.30 
    if model_prob_ml > 0.5:
        ml_pick = partido["home"]
        ml_prob = model_prob_ml
    else:
        ml_pick = partido["away"]
        ml_prob = 1 - model_prob_ml

    # --- 2. OVER/UNDER LEG ---
    model_total_pred = mercados["real_total"] + np.random.normal(0, 7) 
    line = mercados["ou_line"]
    
    if model_total_pred > line:
        ou_pick = "OVER"
        prob_ou = 0.5 + (model_total_pred - line) * 0.02 
    else:
        ou_pick = "UNDER"
        prob_ou = 0.5 + (line - model_total_pred) * 0.02
    
    prob_ou = min(0.75, max(0.25, prob_ou))
    
    # --- 3. COMBINE INTO PARLAY ---
    parlay_prob_real = ml_prob * prob_ou
    parlay_odds = 264 
    
    ev = calculate_ev(parlay_prob_real * 100, parlay_odds)
    
    preds.append({
        "type": "PARLAY",
        "pick_ml": ml_pick,
        "pick_ou": ou_pick,
        "desc": f"{ml_pick} & {ou_pick} {line}",
        "odds": parlay_odds,
        "prob": round(parlay_prob_real*100, 1),
        "ev": ev,
        "line_ou": line
    })

    # return preds  <-- Removing this early return to enable SPREAD logic


    # --- 3. SPREAD ---
    # Modelo predice diferencia de puntos (Home - Away)
    # Spread mercado: Home -5.5 -> Home debe ganar por 6+
    model_spread_pred = mercados["real_diff"] + np.random.normal(0, 6) # Error std dev 6 pts
    spread_line = mercados["spread_line"] # Ej: +5.5 (Home underdog) o -5.5 (Home favorito)
    
    # Si model_spread_pred > spread_line (ej: modelo dice Home gana por 10, spread es -5.5 -> Home cubre)
    # spread_line es positivo si se le SUMA al home? No.
    # Convencion standard: 
    # Spread es "Puntos a sumar al Home para el handicap". 
    # Si Home es favorito (-5.5), spread_line suele representarse negativo.
    # AQUI en simular_mercados_secundarios: 
    # market_spread_line = round(real_diff + noise)
    # Si real_diff es +10 (Home ganó por 10), market_spread_line ~ 10.
    # En apuestas, la linea se presenta como: Home -10.
    # Para apostar a Home, Home Score - 10 > Away Score  =>  Diff > 10.
    
    # Simplificación: 
    # Linea = Valor esperado de margen por el mercado.
    # Si Merc espera +7 (Home gana por 7).
    # Modelo espera +10 (Home gana por 10).
    # Entonces Modelo ve valor en Home -7.
    
    if model_spread_pred > spread_line:
        # Modelo cree que Home lo hará mejor que el mercado -> Apostar Home (Cover)
        spread_pick = partido["home"]
        # Prob = 50% + diferencia * factor
        prob = 0.5 + (model_spread_pred - spread_line) * 0.02
        desc_line = f"{partido['home']} {-spread_line:+.1f}" if spread_line > 0 else f"{partido['home']} {abs(spread_line):+.1f}"
        # Nota: La visualización del spread exacta es compleja, simplificamos para el log
        desc = f"Spread {partido['home']}"
    else:
        # Modelo cree que Home lo hará peor -> Apostar Away (Cover)
        spread_pick = partido["away"]
        prob = 0.5 + (spread_line - model_spread_pred) * 0.02
        desc = f"Spread {partido['away']}"

    prob = min(0.75, max(0.25, prob))
    ev = calculate_ev(prob * 100, -110)

    preds.append({
        "type": "SPREAD",
        "pick": spread_pick,
        "desc": desc,
        "odds": -110,
        "prob": round(prob*100, 1),
        "ev": ev,
        "line": spread_line
    })

    return preds

def ejecutar_total_war():
    print("=" * 70)
    print("🏀 NBA TOTAL WAR - 50% RISK - MULTI-MARKET")
    print("🎯 Moneyline + Over/Under + Spread")
    print("=" * 70)
    
    bankroll = CAPITAL_INICIAL
    total_apuestas = 0
    ganadas = 0
    fecha_actual = FECHA_INICIO
    dias_vividos = 0
    
    while fecha_actual <= FECHA_FIN:
        if bankroll < 1000:
            print("\n💀 QUIEBRA TOTAL - GAME OVER")
            break
            
        print(f"\n[{fecha_actual.strftime('%d/%m/%Y')}] Bankroll: ${bankroll:,.0f}")
        monto_riesgo = bankroll * PORCENTAJE_APUESTA_DIARIO
        stake_unit = monto_riesgo / APUESTAS_POR_DIA
        print(f"   🔥 Risk: ${monto_riesgo:,.0f} (${stake_unit:,.0f} x {APUESTAS_POR_DIA})")
        
        partidos = obtener_partidos_nba(fecha_actual)
        if not partidos:
            fecha_actual += timedelta(days=1)
            continue
            
        pool_apuestas = []
        for p in partidos:
            seed = hash(p["home"] + str(fecha_actual)) % 2**32
            mercados_sim = simular_mercados_secundarios(p, seed)
            
            # Generar predicciones PARLAY
            preds_partido = generar_predicciones_multiples(p, mercados_sim, fecha_actual)
            
            for pred in preds_partido:
                # Evaluar resultado real (AMBAS patas deben cumplirse)
                win_ml = (pred["pick_ml"] == p["winner_real"])
                
                real_tot = p["home_score"] + p["away_score"]
                if pred["pick_ou"] == "OVER": win_ou = real_tot > pred["line_ou"]
                else: win_ou = real_tot < pred["line_ou"]
                
                win = win_ml and win_ou
                
                pred["win"] = win
                pred["match"] = f"{p['home']} vs {p['away']}"
                pool_apuestas.append(pred)
        
        if not pool_apuestas:
             print("   [!] No bets generated for today.")
             fecha_actual += timedelta(days=1)
             continue

        # Seleccionar TODAS las apuestas (All-in strategy)
        pool_apuestas.sort(key=lambda x: x["ev"], reverse=True)
        mejores = pool_apuestas # No limit
        
        num_bets = len(mejores)
        stake_unit = monto_riesgo / num_bets if num_bets > 0 else 0
        print(f"   🔥 Risk: ${monto_riesgo:,.0f} (${stake_unit:,.0f} x {num_bets} bets)")

        balance_dia = 0
        aciertos_dia = 0
        
        for bet in mejores:
            dec_odds = american_to_decimal(bet["odds"])
            if bet["win"]:
                profit = stake_unit * (dec_odds - 1)
                balance_dia += profit
                ganadas += 1
                aciertos_dia += 1
                res = "WIN"
            else:
                profit = -stake_unit
                balance_dia -= stake_unit
                res = "LOSS"
                
            total_apuestas += 1
            print(f"   {res:4} {bet['type']:6} {bet['desc']:25} | EV {bet['ev']}% | {bet['match'][:30]}")
            
        bankroll += balance_dia
        print(f"   Balance Día: {'+' if balance_dia>=0 else ''}${balance_dia:,.0f} ({aciertos_dia}/{len(mejores)})")
        
        dias_vividos += 1
        fecha_actual += timedelta(days=1)
        
    print("\n" + "=" * 70)
    print("📊 RESULTADOS TOTAL WAR")
    ganancia = bankroll - CAPITAL_INICIAL
    wr = (ganadas/total_apuestas*100) if total_apuestas else 0
    
    print(f"Estado: {'💀 QUEBRADO' if bankroll < 1000 else '🏆 SOBREVIVIENTE'}")
    print(f"Días Vividos: {dias_vividos}")
    print(f"Capital Final: ${bankroll:,.0f}")
    print(f"Profit: ${ganancia:,.0f} ({(ganancia/CAPITAL_INICIAL)*100:+.1f}%)")
    print(f"Win Rate: {wr:.1f}% ({ganadas}/{total_apuestas})")
    
    with open("resumen_total_war.txt", "w", encoding="utf-8") as f:
        f.write(f"Capital: ${bankroll:,.0f}\nWR: {wr:.1f}%\n")

if __name__ == "__main__":
    ejecutar_total_war()
