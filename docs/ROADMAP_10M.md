# Estrategia para alcanzar $10 millones COP

**Estrategia definida:** Backfill mejores cuotas + Singles 10% + Capital 5,9M → **10,5M final**.

---

## Resumen ejecutivo

| Parámetro | Valor |
|-----------|-------|
| **Capital inicial** | $5.900.000 |
| **Estrategia** | Singles (3 picks/día, 1 apuesta por pick) |
| **Stake** | 10% por pick |
| **Backfill** | Mejores cuotas (multi-bookmaker) |
| **Capital final** | **$10.561.141** |
| **Win rate** | 73% |

```bash
python backtest_singles.py --fill-odds
```

---

## Alternativas desde $50.000

| Capital inicial | Estrategia | Resultado |
|-----------------|------------|-----------|
| $50.000 | Singles 10% | $89.501 |
| $5.900.000 | Singles 10% | **$10.561.141** |

---

## 1. Backfill con mejores cuotas

El backfill ahora usa las **mejores cuotas** entre todos los bookmakers (bet365, betmgm, draftkings, fanduel, caesars, fanatics) en lugar de solo bet365.

**Impacto:** Mejora el payout cuando ganamos. Parlay pasó de ~$49k a ~$58k. Singles mejoró significativamente.

```bash
# Actualizar TODAS las cuotas a best odds
python backfill_odds_historical.py --all

# O desde el backtest
python backtest_parlay.py --fill-odds
```

---

## 2. Estrategia Singles (recomendada)

En lugar de combinadas de 3 picks, apostar **3 apuestas simples** por día (1 pick cada una).

- **Win rate:** 73% (vs 38% en parlays)
- **Stake óptimo:** 10% por pick
- **Resultado:** $50k → $89.501 (+79%)

```bash
python backtest_singles.py --fill-odds
```

---

## 3. Capital necesario para 10M

| Capital inicial | Estrategia | Resultado |
|----------------|------------|-----------|
| $50.000 | Singles 10% | $89.501 |
| $5.000.000 | Singles 10% | $8.950.119 |
| **$5.900.000** | **Singles 10%** | **$10.561.141** ✓ |

---

## 4. Próximos pasos para mejorar

1. **Mejorar el modelo de predicción** — Win rate > 75% permitiría compound más agresivo
2. **Más datos históricos** — Validar en temporadas completas
3. **Kelly criterion** — Ajustar stake dinámicamente según edge
4. **Filtros adicionales** — Solo apostar cuando EV > umbral

---

*Documento generado — Periodo: 2026-01-01 — 2026-03-06*
