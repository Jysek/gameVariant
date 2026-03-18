# Space Shooter -- Infinite Survival

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
| `P` | **Pausa / Riprendi** |
| `ESC` | Torna al menu |
| `INVIO` | Conferma selezione |

---

## Navicelle

| Nome | Descrizione | Sblocco |
|------|-------------|---------|
| **Falcon** | Cannone centrale, affidabile e precisa | Disponibile da subito |
| **Viper** | Agile e versatile, doppia ala | Disponibile da subito |
| **Phoenix** | Doppio cannone laser, potenza massima | **50 punti** |

---

## Power-up

I power-up appaiono su **navicelle carrier** che scendono dall'alto e si fermano per 5 secondi. Distruggi il carrier per raccogliere il power-up cadente!

| Tipo | Effetto | Durata |
|------|---------|--------|
| Vita | Recupera 1 cuore (max 3) | Istantaneo |
| Scudo | Immunita completa a colpi e contatti nemici (non si rompe) | 5 secondi |
| Velocita | Boost velocita x1.8 | 5 secondi |
| Arma | Sparo triplo/quadruplo angolato | 5 secondi |

---

## Nemici e ostacoli

### Nemici alieni (alien.png -- UFO)
- Tutti i nemici base usano lo sprite `alien.png` (disco volante)
- Si muovono orizzontalmente in formazione e scendono ogni secondo
- Sparano laser verso il basso con pattern diversi per tipo
- Se raggiungono il fondo dello schermo perdi una vita
- Quando colpiti (multi-HP), mostrano un effetto **shake** (nessun overlay bianco)

### Tipi di nemico

| Tipo | HP | Punti | Sparo |
|------|----|-------|-------|
| Scout | 1 | 1 | Laser singolo veloce |
| Fighter | 2 | 2 | Doppio laser parallelo |
| Bomber | 3 | 3 | Laser lento e largo |
| Elite | 2 | 5 | Burst di 3 laser |

### Formazioni (15+)
Le formazioni sono scelte casualmente da un catalogo di 15+ pattern con sistema
anti-ripetizione che impedisce di vedere la stessa formazione due volte di seguito:

H_LINE_3, H_LINE_5, V_LINE_3, GRID_3x2, GRID_4x2, GRID_3x3,
DIAMOND, V_SHAPE, CROSS, T_SHAPE, STAGGER_3x2,
PINCER, ARROW, Z_LINE, WING, CHEVRON, FORTRESS, X_SHAPE

### Asteroidi
- Cadono verticalmente con **scia luminosa realistica**
- **Indistruttibili** con i laser
- Collisione = **game over immediato** (ignora scudo e invincibilita)
- Lo scudo **non protegge** dagli asteroidi

### Carrier power-up
- Scendono dall'alto e si fermano per 5 secondi
- Richiedono 3-5 colpi per essere distrutti
- Se non vengono distrutti, fuggono con uno scatto iperspaziale

---

## Boss Fight

Un boss appare ogni 30-60 secondi di gioco, preceduto da 3 secondi di avviso visivo.

- **4 cannoni** con 3 pattern di sparo casuali
- **Barra della vita** visualizzata in cima allo schermo
- Diventa **piu difficile** ad ogni sconfitta (+10 HP, +velocita, -intervallo sparo)
- Sconfiggerlo assegna **bonus punti** (20 + 5 per ogni boss precedente)

---

## Evento: Pioggia di Asteroidi

Un evento speciale che si attiva ogni 45-90 secondi:

1. **Avviso** di 3 secondi con overlay arancione lampeggiante
2. I nemici vengono rimossi dallo schermo
3. Asteroidi piovono fittamente per 10-25 secondi
4. **Corridoio sicuro garantito**: il sistema garantisce che ci sia sempre
   almeno un percorso di 100px libero da asteroidi
5. Dopo l'evento, cooldown di 40-80 secondi prima del prossimo

---

## Difficolta progressiva

Ogni **30 secondi** di sopravvivenza, la difficolta aumenta di un livello (fino al livello 8):

- I nemici si muovono piu velocemente (+12% per livello)
- Lo spawn interval si accorcia
- Il numero massimo di nemici per ondata aumenta
- Formazioni piu complesse ai livelli alti

Il **livello corrente** e visibile nell'angolo in alto a destra dell'HUD (`Lv.X`).

---

## Salvataggio

Il gioco salva automaticamente in `save_data.json`:
- Record assoluto (high score)
- Top 10 punteggi
- Navicelle sbloccate

---

## Struttura del progetto

```
SpaceShooter/
|-- main.py                  # Entry point
|-- save_data.json           # Salvataggio automatico
|-- README.md                # Questo file
|
|-- core/                    # Infrastruttura condivisa
|   |-- __init__.py
|   |-- assets.py            # Caricamento centralizzato degli asset
|   |-- constants.py         # Costanti globali (schermo, colori, difficolta)
|   |-- save_manager.py      # Salvataggio/caricamento JSON
|   +-- sounds.py            # Audio procedurale + musica di sottofondo
|
|-- entities/                # Entita di gioco
|   |-- __init__.py
|   |-- player.py            # Navicella del giocatore
|   |-- enemy.py             # Nemico con shake all'hit (no overlay bianco)
|   |-- boss.py              # Boss con 4 cannoni e animazione GIF
|   |-- asteroid.py          # Asteroide con corridoio sicuro garantito
|   |-- laser.py             # Laser dritto e angolato (sprite pre-scalati)
|   |-- powerup.py           # Carrier e power-up cadenti
|   |-- explosion.py         # Esplosione animata via GIF
|   |-- formations.py        # 15+ formazioni con anti-ripetizione
|   +-- formation_group.py   # Gruppo di nemici in formazione
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
+-- LaserSprites/            # Sprite laser (66 varianti)
```

---

## Audio

Tutti i suoni -- inclusa la **musica di sottofondo** -- vengono generati
**proceduralmente a runtime** senza alcun file audio esterno.

La musica e un loop ambientale spaziale di 8 secondi composto da tre strati:
- Drone basso pulsante con LFO lento
- Arpeggio pentatonico minore con envelope
- Shimmer cosmico (rumore modulato)

---

## Changelog v6

| Modifica | Descrizione |
|----------|-------------|
| Nemici base | Tutti i nemici usano `alien.png` (UFO) con dimensione 60x44 |
| Formazioni | 15+ formazioni con sistema anti-ripetizione (mai la stessa 2 volte) |
| Hit feedback | Shake sprite (come il boss) invece di overlay bianco sulla hitbox |
| Pioggia asteroidi | Corridoio sicuro garantito (min 100px liberi) |
| Bug fix | `_chk_pl_vs_boss()` -- ciclo laser corretto |
| Bug fix | `_upd_boss_warning` aggiorna formazioni attive durante il warning |
| Bug fix | `reset_game()` pulisce storico formazioni |
| Bug fix | Asteroidi con posizione invalida vengono scartati |
| Refactoring | Commenti professionali, type hints, docstring complete |

---

*Sviluppato con Python -- ITSUmbria 2026*
