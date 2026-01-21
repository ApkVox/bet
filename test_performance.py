"""
Script de prueba para verificar la optimización de rendimiento con asyncio.
"""

import asyncio
import time
from main import analyze_single_prediction, MatchPrediction

async def test_parallel_performance():
    """Prueba de rendimiento simulando 5 partidos"""
    
    # Crear predicciones simuladas
    mock_predictions = [
        MatchPrediction(
            home_team=f"Team A{i}",
            away_team=f"Team B{i}",
            winner=f"Team A{i}",
            win_probability=55.0 + i,
            under_over="OVER",
            ou_line=220.5,
            ou_probability=52.0,
            ai_analysis=None,
            is_mock=True
        )
        for i in range(5)
    ]
    
    print(f"🚀 Iniciando prueba con {len(mock_predictions)} partidos...\n")
    
    # Test 1: Secuencial (simulado)
    print("❌ SECUENCIAL (sin paralelización):")
    start = time.time()
    sequential_results = []
    for pred in mock_predictions:
        result = await analyze_single_prediction(pred)
        sequential_results.append(result)
    sequential_time = time.time() - start
    print(f"   Tiempo total: {sequential_time:.2f}s ({sequential_time/len(mock_predictions):.2f}s por partido)\n")
    
    # Test 2: Paralelo con asyncio.gather
    print("✅ PARALELO (con asyncio.gather):")
    start = time.time()
    tasks = [analyze_single_prediction(pred) for pred in mock_predictions]
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    parallel_time = time.time() - start
    print(f"   Tiempo total: {parallel_time:.2f}s")
    print(f"   Mejora: {sequential_time/parallel_time:.1f}x más rápido\n")
    
    # Resultados
    print("📊 Resultados:")
    for i, result in enumerate(parallel_results):
        if isinstance(result, Exception):
            print(f"   Partido {i+1}: ❌ Error - {str(result)[:50]}")
        else:
            analysis = result.ai_analysis if result.ai_analysis else "Sin análisis"
            print(f"   Partido {i+1}: ✅ {analysis[:60]}...")
    
    print(f"\n🎯 Objetivo alcanzado: Tiempo < 8s: {'✅ SÍ' if parallel_time < 8 else '❌ NO'}")

if __name__ == "__main__":
    asyncio.run(test_parallel_performance())
