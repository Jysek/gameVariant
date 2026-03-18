# Space Shooter -- Infinite Survival v2.0

Un videogioco 2D arcade ispirato a Space Invaders, sviluppato in **Python** con **Pygame**.

**Progetto di:** Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026

---

## Requisiti

| Dipendenza | Versione minima | Installazione |
|------------|----------------|---------------|
| Python     | 3.10+          | [python.org](https://www.python.org) |
| Pygame     | 2.0+           | `pip install pygame` |
| Pillow     | 9.0+           | `pip install Pillow` |

---

## Avvio rapido

```bash
# Installa le dipendenze
pip install pygame Pillow

# Avvia il gioco
python main.py
```

---

## Controlli

| Tasto | Azione |
|-------|--------|
| `W` / freccia su | Muovi su |
| `S` / freccia giu | Muovi giu |
| `A` / freccia sinistra | Muovi sinistra |
| `D` / freccia destra | Muovi destra |
| `SPAZIO` | Spara |
| `B` | Usa bomba |
| `F` | Abilita' speciale (EMP / Overdrive) |
| `P` / `ESC` | **Pausa / Riprendi** |
| `INVIO` | Conferma selezione |
| `A` / `D` | Scegli nave (selezione navi) |

---

## Navicelle (5 giocabili)

Il gioco include **5 navicelle** animate (sprite GIF), ciascuna con **statistiche e abilita' uniche**. Le ultime 2 navi hanno il **doppio cannone**.

| # | Nome | Tipo sparo | Speciale | Sblocco |
|---|------|-----------|----------|---------|
| 0 | **Viper** | Cannone singolo | Nessuna | Disponibile |
| 1 | **Phoenix** | Cannone singolo | Rigenerazione HP | 200 punti |
| 2 | **Striker** | Cannone singolo | Laser perforanti | 500 punti |
| 3 | **Nova** | Doppio cannone | EMP (tasto F) | 1000 punti |
| 4 | **Zenith** | Doppio cannone | Overdrive (tasto F) | 2000 punti |

### Statistiche per nave

| Nave | Velocita' | Rateo fuoco | Danno | Speciale |
|------|-----------|-------------|-------|----------|
| Viper | 1.0x | 1.0x | 1 | Nessuna (bilanciata) |
| Phoenix | 0.8x | 1.3x (lento) | 2 | Rigenera 1 HP ogni 15s |
| Striker | 1.4x (veloce) | 0.6x (rapido) | 1 | Laser attraversano nemici |
| Nova | 1.1x | 0.85x | 1 | EMP: cancella laser nemici e stordisce |
| Zenith | 0.9x | 1.0x | 2 | Overdrive: fuoco rapido 5s (cd 30s) |

Le navi con **doppio cannone** sparano due laser simultanei dai lati. Il power-up *arma* aggiunge laser angolati a tutte le navi.

---

## Nemici (4 tipi animati)

I nemici usano **sprite animati** estratti da `enemy_ships.gif`.

| Tipo | HP | Punti | Sparo | Colore |
|------|----|-------|-------|--------|
| **Scout** | 1 | 1 | Laser singolo veloce | Rosso |
| **Fighter** | 2 | 3 | Doppio laser parallelo | Arancio |
| **Bomber** | 4 | 5 | Laser lento pesante (3 paralleli) | Viola |
| **Elite** | 3 | 8 | Burst di 3 laser rapidi | Ciano |

### Formazioni intelligenti
Le formazioni hanno **tipi misti**: nemici deboli (scout) nelle righe frontali e nemici forti (bomber, elite) nelle righe posteriori. La difficolta' controlla quali tipi sono disponibili.

### Hit feedback (nemici multi-HP)
- **Shake**: oscillazione rapida dello sprite
- **Mini-esplosione**: piccola esplosione animata al punto d'impatto
- **Barra HP**: mostra gli HP rimanenti

---

## Boss Fight (5 varianti)

Ogni boss ha un'**animazione GIF unica** e un **pattern di sparo esclusivo**. Lo spawn del boss e' **casuale con probabilita' uguale** per ognuno dei 5 boss.

| Variante | Nome | Pattern laser | Descrizione |
|----------|------|---------------|-------------|
| 0 | **Titano** | Cannoni rotanti | 4 sub-pattern: dritti, convergenti, divergenti, mirati |
| 1 | **Furia** | Burst devastanti | Raffica + burst secondario automatico |
| 2 | **Ventaglio** | Onde a ventaglio | 7 laser con ampiezza e direzione alternata |
| 3 | **Vortice** | Spirale rotante | 3 bracci che accelerano gradualmente |
| 4 | **Devastatore** | Muro + onde d'urto | 8-12 proiettili in cono + cerchio di laser periodico |

### Scaling progressivo
Ad ogni sconfitta le statistiche del boss successivo crescono:
- +10 HP per boss sconfitto
- +0.3 velocita' orizzontale
- -4 frame intervallo sparo (min 22)
- Bonus punti crescenti

---

## Meccaniche di gioco

### Sistema Combo
Uccidi nemici in rapida successione per accumulare combo:
- 3+ kill: combo visibile
- Moltiplicatore punteggio crescente: +50%, +100%, +150%, +200%, +300%
- Numeri di danno flottanti sullo schermo

### Bombe
- Raccogli dal power-up "Bomba" (max 3)
- Distrugge TUTTI i nemici sullo schermo + cancella laser nemici
- Danneggia il boss per il 25% degli HP residui
- Cooldown di 2 secondi tra usi

### Slow Motion
- Attivato automaticamente dopo aver sconfitto un boss
- Rallenta l'azione per un momento drammatico

### Sistema di vite e protezione
- 3 vite massime
- Invincibilita' temporanea dopo ogni danno
- Lo scudo assorbe colpi e protegge dal danno
- L'asteroide con scudo: scudo si rompe ma nessun danno
- L'asteroide senza scudo: morte istantanea

---

## Power-up

I power-up appaiono su **navicelle carrier** che scendono dall'alto e si fermano per 5 secondi.

| Tipo | Effetto | Durata |
|------|---------|--------|
| **Vita** | Recupera 1 cuore (max 3) | Istantaneo |
| **Scudo** | Assorbe colpi nemici e protegge | 5 secondi |
| **Velocita'** | Boost velocita' x1.8 | 5 secondi |
| **Arma** | Sparo triplo/quadruplo angolato | 5 secondi |
| **Bomba** | +1 bomba (max 3) | Permanente |

---

## Formazioni (18 pattern)

Le formazioni sono scelte casualmente con sistema anti-ripetizione:

`H_LINE_3`, `H_LINE_5`, `V_LINE_3`, `GRID_3x2`, `GRID_4x2`, `GRID_3x3`,
`DIAMOND`, `V_SHAPE`, `CROSS`, `T_SHAPE`, `STAGGER_3x2`,
`PINCER`, `ARROW`, `Z_LINE`, `WING`, `CHEVRON`, `FORTRESS`, `X_SHAPE`

---

## Asteroidi

- Cadono verticalmente con **scia luminosa realistica** (spritesheet animato)
- **Indistruttibili** con i laser
- Collisione senza scudo = **game over immediato**
- Lo scudo assorbe UN colpo da asteroide

### Pioggia di Asteroidi
Evento speciale periodico:
1. **Avviso** di 3 secondi con overlay arancione lampeggiante
2. Asteroidi piovono fittamente per 20-40 secondi
3. **Corridoio sicuro garantito**: almeno 100px liberi da asteroidi

---

## Difficolta' progressiva

Ogni **30 secondi** la difficolta' aumenta (max livello 10):
- Nemici +12% velocita' per livello
- Spawn interval ridotto
- Piu' nemici per ondata
- Formazioni piu' complesse
- Tipi nemico piu' forti sbloccati

---

## Audio

Tutti i suoni -- inclusa la **musica di sottofondo** -- vengono generati
**proceduralmente a runtime** senza file audio esterni.

---

## Salvataggio

Il gioco salva automaticamente in `save_data.json`:
- Record assoluto (high score)
- Top 10 punteggi
- Navicelle sbloccate (5 navi con sblocco progressivo)
- Statistiche cumulative (tempo, uccisioni, boss sconfitti)

Il sistema di salvataggio gestisce automaticamente la **migrazione** da versioni precedenti.

---

## Struttura del progetto

```
SpaceShooter/
|-- main.py                  # Entry point
|-- save_data.json           # Salvataggio automatico
|-- README.md
|
|-- core/                    # Infrastruttura condivisa
|   |-- __init__.py
|   |-- assets.py            # Caricamento centralizzato (GIF/PNG -> Pygame)
|   |-- constants.py         # Costanti globali (5 navi, 5 boss, colori, etc.)
|   |-- save_manager.py      # Salvataggio/caricamento/migrazione JSON
|   +-- sounds.py            # Audio procedurale + musica di sottofondo
|
|-- entities/                # Entita' di gioco
|   |-- __init__.py
|   |-- player.py            # Navicella giocatore (5 navi animate con abilita')
|   |-- enemy.py             # Nemico con sprite GIF animato + shake
|   |-- boss.py              # Boss con 5 varianti + pattern laser unici
|   |-- asteroid.py          # Asteroide con corridoio sicuro
|   |-- laser.py             # Laser dritto/angolato (supporta vx)
|   |-- powerup.py           # Carrier + power-up cadenti
|   |-- explosion.py         # Esplosione animata via GIF
|   |-- formations.py        # 18 formazioni con anti-ripetizione
|   +-- formation_group.py   # Gruppo nemici con tipi misti (deboli davanti)
|
|-- game/
|   |-- __init__.py
|   +-- game.py              # Game loop, stati, spawn, collisioni, HUD
|
|-- world/
|   |-- __init__.py
|   +-- starfield.py         # Sfondo stellare parallax a 3 livelli
|
|-- Assets/                  # Sprite PNG e GIF
|   |-- navicelle.gif        # Navicelle giocatore (3x4 grid, animate)
|   |-- enemy_ships.gif      # 4 tipi nemico (1x4 grid, animate)
|   |-- boss.gif ... boss_4  # 5 varianti boss animate
|   |-- explosionGif.gif     # Esplosione animata
|   |-- asteroid_*.png       # Sprite asteroidi
|   |-- carrier_*.png        # Sprite carrier power-up
|   +-- powerup_*.png        # Sprite power-up cadenti
|
+-- LaserSprites/            # Sprite laser (66 varianti)
```

---

## Changelog

### v2.0 (Release)
- **5 navicelle giocabili** con statistiche e abilita' uniche
- Le ultime 2 navi (Nova, Zenith) hanno il **doppio cannone**
- Punteggi sblocco ribilanciati: 0, 200, 500, 1000, 2000
- 5 boss con **pattern di sparo unici** e spawn **casuale equo**
- Formazioni con **tipi misti** (scout davanti, elite dietro)
- Nuove meccaniche: **bomba**, **EMP**, **piercing**, **overdrive**, **regen**
- **Slow motion** dopo boss kill
- **Combo system** con moltiplicatori
- **Grace period** con countdown (giocatore puo' muoversi)
- Font e testi ridimensionati per leggibilita'
- Bug fix critici (grace period, scudo, invincibilita', direzione boss)
- 45+ test automatizzati superati

### v1.0
- 12 navicelle giocatore animate con sblocco progressivo
- 4 tipi di nemici con sprite animati
- 5 varianti boss con pattern laser unici
- Sistema combo, screen shake, grace period

### v6.0 (legacy)
- 15+ formazioni con anti-ripetizione
- Pioggia asteroidi con corridoio sicuro

---

*Sviluppato con Python 3 / Pygame / Pillow -- ITSUmbria 2026*
