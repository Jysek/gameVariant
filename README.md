# Space Shooter -- Infinite Survival v1.0

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
| `P` / `ESC` | **Pausa / Riprendi** |
| `INVIO` | Conferma selezione |
| `Q` / `E` | Cambia pagina (selezione navi) |

---

## Navicelle (12 disponibili)

Il gioco include **12 navicelle** animate (sprite GIF) organizzate su 3 pagine nella schermata di selezione. Ogni nave ha un'animazione a piu' frame, un colore unico e un pattern di sparo specifico.

| # | Nome | Tipo sparo | Sblocco |
|---|------|-----------|---------|
| 0 | **Falcon** | Cannone singolo | Disponibile |
| 1 | **Viper** | Cannone singolo | Disponibile |
| 2 | **Phoenix** | Doppio cannone | 150 punti |
| 3 | **Raptor** | Cannone singolo | 300 punti |
| 4 | **Striker** | Cannone singolo | 500 punti |
| 5 | **Nova** | Doppio cannone | 750 punti |
| 6 | **Pulsar** | Cannone singolo | 1000 punti |
| 7 | **Nebula** | Cannone singolo | 1500 punti |
| 8 | **Comet** | Doppio cannone | 2000 punti |
| 9 | **Eclipse** | Cannone singolo | 3000 punti |
| 10 | **Tempest** | Cannone singolo | 4500 punti |
| 11 | **Zenith** | Doppio cannone | 6000 punti |

Le navi con **doppio cannone** sparano due laser simultanei dai lati. Il power-up *arma* aggiunge laser angolati a tutte le navi.

---

## Nemici (4 tipi animati)

I nemici usano **sprite animati** estratti da `enemy_ships.gif` (GIF con 6 frame di animazione ciascuno).

| Tipo | HP | Punti | Sparo | Sprite |
|------|----|-------|-------|--------|
| **Scout** | 1 | 1 | Laser singolo veloce | Nave grande rossa |
| **Fighter** | 2 | 2 | Doppio laser parallelo | Nave media blu |
| **Bomber** | 3 | 3 | Laser lento viola | Nave compatta verde |
| **Elite** | 2 | 5 | Burst di 3 laser ciano | Nave piccola dorata |

### Hit feedback (nemici multi-HP)
Quando un nemico con piu' di 1 HP viene colpito da un laser del giocatore (ma non ucciso):
- **Shake**: oscillazione rapida dello sprite (8 frame)
- **Mini-esplosione**: piccola esplosione animata al punto d'impatto

---

## Boss Fight (5 varianti)

Ogni boss ha un'**animazione GIF unica** e un **pattern di sparo esclusivo**.
La variante cambia ad ogni boss sconfitto (rotazione ciclica).

| Variante | GIF | Pattern laser | Descrizione |
|----------|-----|---------------|-------------|
| **Classic** | boss.gif | 3 modalita' casuali | 4 cannoni: tutti/esterni/interni |
| **Burst** | boss_1.gif | Burst veloce | 3 laser ravvicinati dai cannoni esterni |
| **Fan** | boss_2.gif | Ventaglio | 5 laser a ventaglio dal centro |
| **Spiral** | boss_3.gif | Spirale rotante | 2 laser rotanti ad ogni sparo |
| **Shotgun** | boss_4.png | Raffica densa | 5-8 laser in cono largo casuale |

### Scaling progressivo
Ad ogni sconfitta le statistiche del boss successivo crescono:
- +10 HP per boss sconfitto
- +0.3 velocita' orizzontale
- -4 frame intervallo sparo (min 22)
- Bonus punti: 20 + 5 per boss precedente

---

## Power-up

I power-up appaiono su **navicelle carrier** che scendono dall'alto e si fermano per 5 secondi. Distruggi il carrier per raccogliere il power-up cadente!

| Tipo | Effetto | Durata |
|------|---------|--------|
| Vita | Recupera 1 cuore (max 3) | Istantaneo |
| Scudo | Immunita' completa a colpi e contatti nemici | 5 secondi |
| Velocita' | Boost velocita' x1.8 | 5 secondi |
| Arma | Sparo triplo/quadruplo angolato | 5 secondi |

### Carrier hit feedback
I carrier hanno 3-5 HP e mostrano **shake + mini-esplosione** quando colpiti (come i nemici multi-HP).

---

## Formazioni (15+ pattern)

Le formazioni sono scelte casualmente con sistema anti-ripetizione:

`H_LINE_3`, `H_LINE_5`, `V_LINE_3`, `GRID_3x2`, `GRID_4x2`, `GRID_3x3`,
`DIAMOND`, `V_SHAPE`, `CROSS`, `T_SHAPE`, `STAGGER_3x2`,
`PINCER`, `ARROW`, `Z_LINE`, `WING`, `CHEVRON`, `FORTRESS`, `X_SHAPE`

---

## Asteroidi

- Cadono verticalmente con **scia luminosa realistica** (spritesheet animato)
- **Indistruttibili** con i laser
- Collisione = **game over immediato** (ignora scudo e invincibilita')

### Pioggia di Asteroidi
Evento speciale ogni 45-90 secondi:
1. **Avviso** di 3 secondi con overlay arancione lampeggiante
2. Asteroidi piovono fittamente per 10-25 secondi
3. **Corridoio sicuro garantito**: almeno 100px liberi da asteroidi

---

## Difficolta' progressiva

Ogni **30 secondi** la difficolta' aumenta (max livello 8):
- Nemici +12% velocita' per livello
- Spawn interval ridotto
- Piu' nemici per ondata
- Formazioni piu' complesse

---

## Audio

Tutti i suoni -- inclusa la **musica di sottofondo** -- vengono generati
**proceduralmente a runtime** senza file audio esterni.

---

## Salvataggio

Il gioco salva automaticamente in `save_data.json`:
- Record assoluto (high score)
- Top 10 punteggi
- Navicelle sbloccate (12 navi con sblocco progressivo)

Il sistema di salvataggio gestisce automaticamente la **migrazione** da versioni precedenti (3 navi -> 12 navi).

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
|   |-- constants.py         # Costanti globali (12 navi, 5 boss, colori, etc.)
|   |-- save_manager.py      # Salvataggio/caricamento/migrazione JSON
|   +-- sounds.py            # Audio procedurale + musica di sottofondo
|
|-- entities/                # Entita' di gioco
|   |-- __init__.py
|   |-- player.py            # Navicella giocatore (12 navi animate)
|   |-- enemy.py             # Nemico con sprite GIF animato + shake
|   |-- boss.py              # Boss con 5 varianti + pattern laser unici
|   |-- asteroid.py          # Asteroide con corridoio sicuro
|   |-- laser.py             # Laser dritto/angolato (supporta vx)
|   |-- powerup.py           # Carrier + power-up cadenti
|   |-- explosion.py         # Esplosione animata via GIF
|   |-- formations.py        # 15+ formazioni con anti-ripetizione
|   +-- formation_group.py   # Gruppo nemici in formazione
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
|   |-- navicelle.gif        # 12 navicelle giocatore (3x4 grid, animate)
|   |-- enemy_ships.gif      # 4 tipi nemico (1x4 grid, animate)
|   |-- boss.gif             # Boss variante 0 (Classic)
|   |-- boss_1.gif           # Boss variante 1 (Burst)
|   |-- boss_2.gif           # Boss variante 2 (Fan)
|   |-- boss_3.gif           # Boss variante 3 (Spiral)
|   |-- boss_4.png           # Boss variante 4 (Shotgun, spritestrip)
|   |-- explosionGif.gif     # Esplosione animata
|   |-- asteroid_*.png       # Sprite asteroidi
|   |-- carrier_*.png        # Sprite carrier power-up
|   |-- powerup_*.png        # Sprite power-up cadenti
|   |-- asteroid_trail.png   # Spritesheet scia asteroide
|   |-- ships/               # Navicelle ritagliate (generate)
|   +-- enemies/             # Nemici ritagliati (generati)
|
+-- LaserSprites/            # Sprite laser (66 varianti)
```

---

## Changelog

### v1.0 (Release)
- 12 navicelle giocatore animate da GIF con sblocco progressivo
- 4 tipi di nemici con sprite animati da GIF
- 5 varianti boss con pattern laser unici
- Mini-esplosione + shake su hit di entita' multi-HP (nemici, carrier, boss)
- Selezione nave con griglia paginata (4 per pagina, Q/E per cambiare)
- Sistema di sblocco esteso (12 livelli di punteggio)
- Migrazione automatica save da versioni precedenti
- Laser con velocita' orizzontale per i pattern boss avanzati
- Code refactoring completo e bug fixes

### v6.0
- Nemici base con `alien.png` (UFO)
- 15+ formazioni con anti-ripetizione
- Shake sprite (no overlay bianco) per nemici multi-HP
- Pioggia asteroidi con corridoio sicuro

---

*Sviluppato con Python 3 / Pygame / Pillow -- ITSUmbria 2026*
