# Análisis de Backtest: Combinada Diaria — Estrategia Optimizada (meta 10M)

**La Fija** — Meta: $10M ganancia. Estrategia optimizada para maximizar rentabilidad.

---

## Metodología

- **Capital inicial:** $50.000 COP  
- **Stake:** 5% base, 7% cuando min prob ≥ 85%, 4% tras 2 pérdidas  
- **Selección de picks:** Las 3 predicciones con mayor puntuación; prob ≥ 80% (fallback 75%→70%→65%). Scoring: 70% prob, 20% EV.  
- **Periodo:** 2026-01-01 — 2026-03-06  
- **Cuotas:** Reales desde sbrscrape (backfill automático).

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Capital final | $58,422 |
| Retorno (%) | +16.84% |
| Días apostados | 52 |
| Combinadas ganadas | 20 |
| Combinadas perdidas | 32 |
| Días omitidos | 6 |

---

## Detalle por día

| Fecha | Apuesta | Cuota | Resultado | Capital |
|-------|---------------|-------|-----------|---------|
| 2026-01-01 | $3,500 | 3.0 | **GANADA** | $57,000 |
| 2026-01-02 | $3,990 | 3.612 | **GANADA** | $67,422 |
| 2026-01-03 | $4,720 | 2.595 | **PERDIDA** | $62,702 |
| 2026-01-04 | $4,389 | 2.704 | **GANADA** | $70,181 |
| 2026-01-05 | $4,913 | 13.28 | **PERDIDA** | $65,269 |
| 2026-01-06 | $4,569 | 2.821 | **PERDIDA** | $60,700 |
| 2026-01-07 | $2,428 | 8.084 | **GANADA** | $77,900 |
| 2026-01-09 | $5,453 | 2.327 | **PERDIDA** | $72,447 |
| 2026-01-10 | $5,071 | 4.097 | **PERDIDA** | $67,376 |
| 2026-01-11 | $2,695 | 1.735 | **GANADA** | $69,356 |
| 2026-01-12 | $4,855 | 2.348 | **PERDIDA** | $64,502 |
| 2026-01-13 | $4,515 | 2.622 | **GANADA** | $71,825 |
| 2026-01-14 | $5,028 | 4.888 | **PERDIDA** | $66,797 |
| 2026-01-15 | $4,676 | 3.628 | **PERDIDA** | $62,121 |
| 2026-01-16 | $2,485 | 13.806 | **PERDIDA** | $59,637 |
| 2026-01-17 | $2,385 | 1.839 | **GANADA** | $61,638 |
| 2026-01-18 | $4,315 | 4.698 | **PERDIDA** | $57,323 |
| 2026-01-19 | $4,013 | 1.945 | **GANADA** | $61,115 |
| 2026-01-20 | $4,278 | 2.937 | **PERDIDA** | $56,837 |
| 2026-01-21 | $3,979 | 2.598 | **GANADA** | $63,195 |
| 2026-01-22 | $4,424 | 2.336 | **PERDIDA** | $58,771 |
| 2026-01-23 | $4,114 | 1.677 | **PERDIDA** | $54,657 |
| 2026-01-24 | $2,186 | 3.678 | **PERDIDA** | $52,471 |
| 2026-01-25 | $2,099 | 1.73 | **PERDIDA** | $50,372 |
| 2026-01-26 | $2,015 | 3.287 | **PERDIDA** | $48,357 |
| 2026-01-28 | $1,934 | 10.441 | **GANADA** | $66,619 |
| 2026-01-29 | $4,663 | 4.551 | **PERDIDA** | $61,956 |
| 2026-01-30 | $4,337 | 3.49 | **PERDIDA** | $57,619 |
| 2026-02-01 | $2,305 | 2.651 | **GANADA** | $61,424 |
| 2026-02-04 | $4,300 | 12.496 | **PERDIDA** | $57,124 |
| 2026-02-05 | $3,999 | 1.845 | **PERDIDA** | $53,126 |
| 2026-02-06 | $2,125 | 3.069 | **PERDIDA** | $51,001 |
| 2026-02-08 | $2,040 | 2.57 | **PERDIDA** | $48,961 |
| 2026-02-09 | $1,958 | 4.749 | **PERDIDA** | $47,002 |
| 2026-02-10 | $1,880 | 1.842 | **PERDIDA** | $45,122 |
| 2026-02-11 | $1,805 | 2.551 | **GANADA** | $47,921 |
| 2026-02-12 | $3,354 | 2.342 | **PERDIDA** | $44,567 |
| 2026-02-19 | $3,120 | 2.218 | **PERDIDA** | $41,447 |
| 2026-02-20 | $1,658 | 2.447 | **GANADA** | $43,846 |
| 2026-02-21 | $3,069 | 2.014 | **PERDIDA** | $40,777 |
| 2026-02-22 | $2,854 | 4.224 | **GANADA** | $49,980 |
| 2026-02-23 | $3,499 | 3.663 | **PERDIDA** | $46,481 |
| 2026-02-24 | $3,254 | 3.121 | **PERDIDA** | $43,227 |
| 2026-02-25 | $1,729 | 2.946 | **PERDIDA** | $41,498 |
| 2026-02-26 | $1,660 | 2.352 | **GANADA** | $43,742 |
| 2026-02-27 | $3,062 | 1.888 | **GANADA** | $46,461 |
| 2026-02-28 | $3,252 | 2.883 | **PERDIDA** | $43,209 |
| 2026-03-01 | $3,025 | 1.486 | **GANADA** | $44,679 |
| 2026-03-02 | $3,128 | 2.255 | **GANADA** | $48,604 |
| 2026-03-03 | $3,402 | 1.885 | **GANADA** | $51,615 |
| 2026-03-04 | $3,613 | 2.143 | **PERDIDA** | $48,002 |
| 2026-03-05 | $3,360 | 4.101 | **GANADA** | $58,422 |

**Partidos que fallaron:**

- Portland Trail Blazers @ San Antonio Spurs
- Houston Rockets @ Dallas Mavericks
- Charlotte Hornets @ Oklahoma City Thunder
- Golden State Warriors @ LA Clippers
- Orlando Magic @ Washington Wizards
- Houston Rockets @ Portland Trail Blazers
- Miami Heat @ Indiana Pacers
- LA Clippers @ Detroit Pistons
- Los Angeles Lakers @ Sacramento Kings
- Boston Celtics @ Indiana Pacers
- Utah Jazz @ Cleveland Cavaliers
- New York Knicks @ Sacramento Kings
- Atlanta Hawks @ Portland Trail Blazers
- Washington Wizards @ Sacramento Kings
- LA Clippers @ Toronto Raptors
- Minnesota Timberwolves @ Houston Rockets
- Charlotte Hornets @ Denver Nuggets
- Minnesota Timberwolves @ Utah Jazz
- Toronto Raptors @ Golden State Warriors
- Golden State Warriors @ Dallas Mavericks
- Indiana Pacers @ Oklahoma City Thunder
- Boston Celtics @ Chicago Bulls
- New Orleans Pelicans @ San Antonio Spurs
- Philadelphia 76ers @ Charlotte Hornets
- Milwaukee Bucks @ Washington Wizards
- Memphis Grizzlies @ New Orleans Pelicans
- Oklahoma City Thunder @ San Antonio Spurs
- Washington Wizards @ Detroit Pistons
- New Orleans Pelicans @ Minnesota Timberwolves
- New York Knicks @ Boston Celtics
- Utah Jazz @ Miami Heat
- Philadelphia 76ers @ Portland Trail Blazers
- Indiana Pacers @ New York Knicks
- Milwaukee Bucks @ Oklahoma City Thunder
- Denver Nuggets @ LA Clippers
- Philadelphia 76ers @ New Orleans Pelicans
- Sacramento Kings @ Memphis Grizzlies
- San Antonio Spurs @ Detroit Pistons
- Golden State Warriors @ New Orleans Pelicans
- Cleveland Cavaliers @ Milwaukee Bucks
- Houston Rockets @ Miami Heat
- Charlotte Hornets @ Boston Celtics

---

## Meta 10M y limitaciones

Con los datos históricos (52 días, 20 ganadas, 32 perdidas), el mejor resultado es ~$58,422. Para llegar a **$10M** se necesitaría:

- **Tasa de acierto > 55%** — Actual 38% limita el compound.
- **Más días con prob ≥ 90%** — Misma tasa; los filtros no mejoran el historial.
- **Capital inicial ~$9M** — Con 9M y 5% stake se alcanza 10,3M (simulado).

| Capital inicial | Estrategia | Resultado |
|-----------------|------------|-----------|
| $50.000 | Parlay 5% | ~$58,422 |
| $50.000 | Singles 10% | ~$89.501 |
| **$5.900.000** | **Singles 10%** | **$10.561.141** ✓ |

**Estrategia 10M:** docs/ROADMAP_10M.md — Singles 10%, capital $5,9M → $10,5M final.


**Última combinada ganada:**

- Brooklyn Nets @ Miami Heat -> Miami Heat (WIN)
- Toronto Raptors @ Minnesota Timberwolves -> Minnesota Timberwolves (WIN)
- Utah Jazz @ Washington Wizards -> Utah Jazz (WIN)
---

## Roadmap hacia 10M

Ver **docs/ROADMAP_10M.md** — Backfill mejores cuotas + estrategia Singles (73% win rate) → $89.501.

## Cómo ejecutar

```bash
python backtest_parlay.py --fill-odds --update-doc
python backtest_singles.py --fill-odds   # Singles (recomendada para 10M)
```

---

*Documento actualizado — Periodo: 2026-01-01 — 2026-03-06*