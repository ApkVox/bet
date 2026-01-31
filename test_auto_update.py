"""
Test de Actualizacion Automatica de Marcadores
=============================================
Este script verifica que el sistema de actualizacion automatica funciona correctamente:
1. Verifica que la base de datos existe
2. Verifica predicciones pendientes
3. Ejecuta la funcion de actualizacion
4. Muestra resultados
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configurar path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def test_database_exists():
    """Verifica que la base de datos de historial existe"""
    print("\n" + "="*50)
    print("TEST 1: Verificar base de datos")
    print("="*50)
    
    import history_db
    db_path = history_db.DB_PATH
    
    if db_path.exists():
        print(f"✅ Base de datos encontrada: {db_path}")
        return True
    else:
        print(f"⚠️ Base de datos no existe: {db_path}")
        print("   Inicializando...")
        history_db.init_history_db()
        return True


def test_get_pending_predictions():
    """Verifica si hay predicciones pendientes"""
    print("\n" + "="*50)
    print("TEST 2: Buscar predicciones pendientes")
    print("="*50)
    
    import sqlite3
    import history_db
    
    with sqlite3.connect(history_db.DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, COUNT(*) as count 
            FROM predictions 
            WHERE result = 'PENDING' 
            GROUP BY date
            ORDER BY date DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print(f"✅ Encontradas predicciones pendientes:")
            for date, count in rows:
                print(f"   📅 {date}: {count} predicciones")
            return True
        else:
            print("ℹ️ No hay predicciones pendientes (todas resueltas o ninguna guardada)")
            return True


def test_update_pending_predictions():
    """Ejecuta la función de actualización y muestra resultados"""
    print("\n" + "="*50)
    print("TEST 3: Ejecutar actualización automática")
    print("="*50)
    
    try:
        from src.Services.history_service import update_pending_predictions
        
        print("Ejecutando update_pending_predictions()...")
        result = update_pending_predictions()
        
        print(f"\n✅ Resultado: {result}")
        
        if result.get('updated_count', 0) > 0:
            print(f"   🎉 Se actualizaron {result['updated_count']} partidos con sus scores reales")
        else:
            print("   ℹ️ No se actualizaron partidos (puede que no haya scores disponibles aún)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_updated_results():
    """Verifica el estado después de la actualización"""
    print("\n" + "="*50)
    print("TEST 4: Verificar resultados actualizados")
    print("="*50)
    
    import sqlite3
    import history_db
    
    with sqlite3.connect(history_db.DB_PATH) as conn:
        # Contar por estado
        cursor = conn.execute("""
            SELECT result, COUNT(*) as count 
            FROM predictions 
            GROUP BY result
        """)
        
        rows = cursor.fetchall()
        
        print("📊 Estado de predicciones en BD:")
        for result, count in rows:
            emoji = "✅" if result in ["WIN", "LOSS"] else "⏳" if result == "PENDING" else "❓"
            print(f"   {emoji} {result}: {count}")
        
        # Mostrar últimos 5 partidos resueltos
        cursor = conn.execute("""
            SELECT date, match_id, predicted_winner, result, profit
            FROM predictions
            WHERE result IN ('WIN', 'LOSS')
            ORDER BY date DESC
            LIMIT 5
        """)
        
        resolved = cursor.fetchall()
        if resolved:
            print("\n📋 Últimos partidos resueltos:")
            for date, match, prediction, result, profit in resolved:
                emoji = "✅" if result == "WIN" else "❌"
                print(f"   {emoji} {date}: {match} → {result} (Predicción: {prediction}, Profit: {profit})")
        
        return True


def main():
    print("\n" + "="*60)
    print("🏀 TEST DE ACTUALIZACIÓN AUTOMÁTICA DE MARCADORES NBA")
    print("="*60)
    
    tests = [
        ("Database Exists", test_database_exists),
        ("Get Pending Predictions", test_get_pending_predictions),
        ("Update Pending Predictions", test_update_pending_predictions),
        ("Check Updated Results", test_check_updated_results),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    all_passed = True
    for name, success in results:
        emoji = "✅" if success else "❌"
        print(f"   {emoji} {name}")
        if not success:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASARON CORRECTAMENTE")
    else:
        print("⚠️ ALGUNOS TESTS FALLARON")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
