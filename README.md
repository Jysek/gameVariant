# 🚀 Space Shooter — Infinite Survival

Un videogioco 2D arcade ispirato a Space Invaders, sviluppato in **Python** con **Pygame**.

**Progetto di:** Ceccariglia Emanuele & Andrea Cestelli — ITSUmbria 2026

---

## 📋 Requisiti

| Dipendenza | Versione minima | Installazione |
|------------|----------------|---------------|
| Python     | 3.10+          | [python.org](https://www.python.org) |
| Pygame     | 2.0+           | `pip install pygame` |
| Pillow     | 9.0+           | `pip install Pillow` |

---

## ▶️ Avvio rapido

```bash
# Installa le dipendenze
pip install pygame Pillow

# Avvia il gioco
python main.py
```

---

## 🎮 Controlli

| Tasto | Azione |
|-------|--------|
| `W` / `↑` | Muovi su |
| `S` / `↓` | Muovi giù |
| `A` / `←` | Muovi sinistra |
| `D` / `→` | Muovi destra |
| `SPAZIO` | Spara |
| `P` | **Pausa / Riprendi** |
| `ESC` | Torna al menu |
| `INVIO` | Conferma selezione |

---

## 🛸 Navicelle

| Nome | Descrizione | Sblocco |
|------|-------------|---------|
| **Falcon** | Cannone centrale, affidabile e precisa | Disponibile da subito |
| **Viper** | Agile e versatile, doppia ala | Disponibile da subito |
| **Phoenix** | Doppio cannone laser, potenza massima | **50 punti** |

---

## ⚡ Power-up

I power-up appaiono su **navicelle carrier** che scendono dall'alto e si fermano per 5 secondi. Distruggi il carrier per raccogliere il power-up cadente!

| Icona | Tipo | Effetto | Durata |
|-------|------|---------|--------|
| ❤️ Vita | Recupera 1 cuore (max 3) | Istantaneo |
| 🛡️ Scudo | Immunità completa a colpi e contatti nemici (non si rompe) | 5 secondi |
| ⚡ Velocità | Boost velocità ×1.8 | 5 secondi |
| 🔫 Arma | Sparo triplo/quadruplo angolato | 5 secondi |

---

## 👾 Nemici e ostacoli

### Nemici alieni
- Si muovono orizzontalmente e scendono ogni secondo
- Sparano laser verso il basso
- Se raggiungono il fondo dello schermo perdi una vita

### Asteroidi ☄️
- Cadono verticalmente con **scia luminosa realistica**
- **Indistruttibili** con i laser
- Collisione = **game over immediato** (ignora scudo e invincibilità)
- Lo scudo **non protegge** dagli asteroidi: la navicella viene distrutta comunque

### Carrier power-up
- Scendono dall'alto e si fermano per 5 secondi
- Richiedono 3–5 colpi per essere distrutti
- Se non vengono distrutti, fuggono con uno scatto iperspaziale

---

## 🔴 Boss Fight

Un boss appare ogni 30–60 secondi di gioco, preceduto da 3 secondi di avviso visivo.

- **4 cannoni** con 3 pattern di sparo casuali
- **Barra della vita** visualizzata in cima allo schermo
- Diventa **più difficile** ad ogni sconfitta (+10 HP, +velocità, -intervallo sparo)
- Sconfiggerlo assegna **bonus punti** (20 + 5 per ogni boss precedente)

---

## ☄️ Evento: Pioggia di Asteroidi

Un evento speciale che si attiva ogni 45–90 secondi:

1. **Avviso** di 3 secondi con overlay arancione lampeggiante
2. I nemici vengono rimossi dallo schermo
3. Asteroidi piovono fittamente per 10–25 secondi
4. **Obiettivo:** schiva tutto! Il giocatore può ancora sparare ma i laser non servono
5. Dopo l'evento, cooldown di 40–80 secondi prima del prossimo

---

## 📈 Difficoltà progressiva

Ogni **30 secondi** di sopravvivenza, la difficoltà aumenta di un livello (fino al livello 8):

- I nemici si muovono più velocemente (+12% per livello)
- Lo spawn interval si accorcia
- Il numero massimo di nemici per ondata aumenta

Il **livello corrente** è visibile nell'angolo in alto a destra dell'HUD (`Lv.X`).

---

## 💾 Salvataggio

Il gioco salva automaticamente in `save_data.json`:
- Record assoluto (high score)
- Top 10 punteggi
- Navicelle sbloccate

---

## 🏗️ Struttura del progetto

```
Game_with_PYTHON/
├── main.py                  # Entry point
├── save_data.json           # Salvataggio automatico
├── README.md                # Questo file
│
├── core/                    # Infrastruttura condivisa
│   ├── assets.py            # Caricamento centralizzato degli asset
│   ├── constants.py         # Costanti globali (schermo, colori, difficoltà)
│   ├── save_manager.py      # Salvataggio/caricamento JSON
│   └── sounds.py            # Audio procedurale + musica di sottofondo
│
├── entities/                # Entità di gioco
│   ├── player.py            # Navicella del giocatore
│   ├── enemy.py             # Navicella nemica (con scaling difficoltà)
│   ├── boss.py              # Boss con 4 cannoni e animazione GIF
│   ├── asteroid.py          # Asteroide con scia luminosa + anti-overlap
│   ├── laser.py             # Laser dritto e angolato (sprite pre-scalati)
│   ├── powerup.py           # Carrier e power-up cadenti
│   └── explosion.py         # Esplosione animata via GIF
│
├── game/
│   └── game.py              # Game loop, stati, spawn, collisioni, HUD
│
├── world/
│   └── starfield.py         # Sfondo stellare parallax a 3 livelli
│
├── Assets/                  # Sprite PNG e GIF
└── LaserSprites/            # Sprite laser (66 varianti)
```

---

## 🔊 Audio

Tutti i suoni — inclusa la **musica di sottofondo** — vengono generati **proceduralmente a runtime** senza alcun file audio esterno.

La musica è un loop ambientale spaziale di 8 secondi composto da tre strati sovrapposti:
- Drone basso pulsante con LFO lento
- Arpeggio pentatonico minore con envelope
- Shimmer cosmico (rumore modulato)

---

## ✅ Bug risolti rispetto alla versione 1.0

| Bug | Descrizione | Fix |
|-----|-------------|-----|
| Spawn nemici | Ramo `else` irraggiungibile nella logica del conteggio | Logica semplificata con `if/elif/else` corretti |
| Performance laser | `transform.scale()` chiamato ogni frame per ogni proiettile | Sprite pre-scalati una volta in `Assets.load()` |
| Boss collisione | Collisione diretta boss→giocatore non riproduceva `game_over` sound | Delegato a `_player_death_explosion()` che include il suono |
| Asteroidi overlap | Asteroidi spawnati nella stessa colonna rendevano la pioggia impossibile | Registro globale anti-sovrapposizione + spawn distribuito in colonne |
| Asteroidi velocità | Velocità massima troppo alta (4.5) rendeva impossibile schivare | Cap ridotto a 3.6, intervallo spawn pioggia allargato |

---

*Sviluppato con ❤️ in Python — ITSUmbria 2026*
