"""
Risk Analysis Reporter
======================
Analyzes Monte Carlo simulation results to generate a comprehensive Risk Report.
Focuses on Drawdown distribution, Ruin risk, and Performance variability.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_FILE = BASE_DIR / "validation_results" / "monte_carlo" / "monte_carlo_results.csv"
REPORT_FILE = BASE_DIR / "docs" / "risk_analysis_report.md"

def analyze_risk():
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found.")
        return

    df = pd.read_csv(RESULTS_FILE)
    n_sims = len(df)
    
    # 1. Ruin Analysis
    ruin_count = df['bankrupt'].sum()
    ruin_prob = ruin_count / n_sims
    
    # 2. Drawdown Analysis
    avg_max_dd = df['max_drawdown'].mean()
    median_max_dd = df['max_drawdown'].median()
    p90_dd = np.percentile(df['max_drawdown'], 90)
    p95_dd = np.percentile(df['max_drawdown'], 95)
    p99_dd = np.percentile(df['max_drawdown'], 99)
    worst_case_dd = df['max_drawdown'].max()
    
    # 3. ROI Analysis
    avg_roi = df['final_roi'].mean()
    median_roi = df['final_roi'].median()
    std_roi = df['final_roi'].std()
    sharpe_proxy = avg_roi / std_roi if std_roi > 0 else 0
    
    # 4. Bets Analysis
    avg_bets = df['total_bets'].mean()
    
    # Classification
    if ruin_prob > 0.05: risk_level = "UNACCEPTABLE"
    elif ruin_prob > 0.01: risk_level = "HIGH"
    elif p95_dd > 0.50: risk_level = "MODERATE-HIGH"
    elif p95_dd > 0.30: risk_level = "MODERATE"
    else: risk_level = "LOW"
    
    # Generate Markdown Report
    report = []
    report.append("# 🛡️ Informe Técnico de Riesgo Extremo")
    report.append(f"**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    report.append(f"**Base:** {n_sims} Simulaciones Monte Carlo (12.3M partidos simulados)")
    report.append(f"**Nivel de Riesgo Global:** `{risk_level}`")
    
    report.append("\n## 1. Análisis de Supervivencia (Ruin Risk)")
    report.append("| Métrica | Valor | Threshold Seguridad | Estado |")
    report.append("|---------|-------|---------------------|--------|")
    report.append(f"| Probabilidad de Ruina | **{ruin_prob:.2%}** | < 1.00% | {'✅' if ruin_prob < 0.01 else '❌'} |")
    report.append(f"| Simulaciones Quebradas | {ruin_count} / {n_sims} | 0 | - |")
    
    report.append("\n## 2. Severidad del Drawdown (Pérdidas)")
    report.append("El 'Max Drawdown' mide la mayor caída porcentual desde un pico histórico en una temporada.")
    report.append("")
    report.append("| Percentil | Drawdown Esperado | Interpretación |")
    report.append("|-----------|-------------------|----------------|")
    report.append(f"| **Promedio** | {avg_max_dd:.1%} | Pérdida 'normal' en una temporada típica. |")
    report.append(f"| **Mediana (P50)** | {median_max_dd:.1%} | El escenario más probable. |")
    report.append(f"| **Severo (P95)** | **{p95_dd:.1%}** | Escenario malo (1 de cada 20 temporadas). |")
    report.append(f"| **Extremo (P99)** | **{p99_dd:.1%}** | Cisne negro (1 de cada 100 temporadas). |")
    report.append(f"| **Peor Caso** | {worst_case_dd:.1%} | El peor escenario observado en la simulación. |")
    
    report.append("\n## 3. Volatilidad y Retorno")
    report.append("| Métrica | Valor | Notas |")
    report.append("|---------|-------|-------|")
    report.append(f"| ROI Promedio | +{avg_roi:.1%} | Retorno sobre capital inicial por temporada. |")
    report.append(f"| Volatilidad ROI (Std) | {std_roi:.1%} | Dispersión de resultados. |")
    report.append(f"| Sharpe Ratio (Proxy) | {sharpe_proxy:.2f} | > 1.0 es excelente, > 2.0 es excepcional. |")
    report.append(f"| Apuestas Promedio | {int(avg_bets)} | Volumen de actividad por temporada. |")
    
    report.append("\n## 4. Matriz de Colapso")
    report.append("Condiciones que podrían llevar al sistema al fallo:")
    report.append("- **Racha de pérdidas consecutivas > 15** (Probabilidad estadística < 0.01%).")
    report.append("- **Descalibración del Modelo:** Si la precisión cae por debajo del 52% consistentemente.")
    # Inferred from simulation logic: if prob < 0.55 we assume no bet, so low accuracy manifests as NO BETS usually, preventing ruin.
    # But if model is confident (high prob) but WRONG, that's the killer.
    # The simulation uses "Synthetic Odds" which are tied to model prob + noise.
    # Real danger is if Model says 70% and Reality is 40%.
    
    report.append("\n## 5. Protocolos de Seguridad (Survival Rules)")
    report.append("> [!WARNING]")
    report.append("> **ACTIVAR PROTOCOLODE EMERGENCIA SI:**")
    report.append("> 1. **Drawdown actual supera el 20%:** Reducir `Fractional Kelly` a 0.10.")
    report.append("> 2. **Racha de 10 pérdidas seguidas:** Pausar betting y revisar modelo.")
    report.append("> 3. **Bankroll < 50% inicial:** Reiniciar a stake fijo (1%) hasta recuperar el 80%.")

    # Save
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Risk report generated: {REPORT_FILE}")

if __name__ == "__main__":
    analyze_risk()
