# MyHome Timer — Custom Component per Home Assistant

Integrazione che espone il servizio `myhome_timer.turn_on_timed` per
inviare comandi timer nativi SCS/BTicino sul bus OpenWebNet, tramite
`myhome.send_message` (componente anotherjulien/MyHOME v0.8.6+).

---

## Struttura file

```
config/
├── custom_components/
│   └── myhome_timer/
│       ├── __init__.py
│       ├── manifest.json
│       └── services.yamL
```

---

## Installazione

### 1. Copia il custom component

Copia la cartella `custom_components/myhome_timer/` dentro
`/config/custom_components/` sulla tua installazione HA OS.

Via **Samba** o **SSH + File Editor**:
```
/config/custom_components/myhome_timer/__init__.py
/config/custom_components/myhome_timer/manifest.json
/config/custom_components/myhome_timer/services.yaml
```

### 2. Aggiungi al configuration.yaml

```yaml
myhome_timer:
```

Basta questa riga. Il componente si aggancia a `myhome` che deve
essere già installato e funzionante.

### 3. Riavvia Home Assistant

Da Impostazioni → Sistema → Riavvia.

### 4. Verifica

Vai in **Strumenti di sviluppo → Servizi**, cerca `myhome_timer.turn_on_timed`.
Dovresti vedere il servizio con tutti i campi descritti.

---

## Utilizzo del servizio (Approccio 1)

### Esempio da UI Strumenti sviluppatore:

```yaml
service: myhome_timer.turn_on_timed
data:
  entity_id: light.luce_portone
  timer_mode: "15min"
```

Questo invierà automaticamente: `*1*16*<A><PL>##`

### Modalità custom (durata arbitraria):

```yaml
service: myhome_timer.turn_on_timed
data:
  entity_id: light.luce_portone
  timer_mode: "custom"
  hours: 0
  minutes: 20
  seconds: 0
```

Frame inviato: `*#1*<WHERE>*#2*0*20*0##`

---

## Blueprint (Approccio 2)

### Installazione blueprint

Cerca la repo "blueprint trigger timer myhome"

Copia `myhome_timer_blueprint.yaml` in:
```
/config/blueprints/automation/myhome_timer_blueprint.yaml
```

Poi in HA: **Impostazioni → Automazioni → Blueprint → Importa**.


L'automazione sostituisce il blocco `myhome.send_message` manuale con un'interfaccia guidata.

---

## Come il componente ricava A e PL

Il componente cerca negli attributi dell'entità luce (nell'ordine):

1. Attributo `where` → usato direttamente
2. Attributi `a` + `pl`
3. Attributi `area` + `pl`
4. Attributi `a` + `point_light`
5. Attributi `a` + `light_point`

Per vedere gli attributi della tua entità:
**Strumenti sviluppatore → Stati → cerca la tua luce myhome**

---

## Tabella WHAT timer OWN (WHO=1, §
par3.1 who=1)

| timer_mode | WHAT | Frame inviato         | Durata    |
|------------|------|-----------------------|-----------|
| 0.5sec     |  18  | `*1*18*<WHERE>##`     | 0.5 sec   |
| 30sec      |  17  | `*1*17*<WHERE>##`     | 30 sec    |
| 1min       |  11  | `*1*11*<WHERE>##`     | 1 min     |
| 2min       |  12  | `*1*12*<WHERE>##`     | 2 min     |
| 3min       |  13  | `*1*13*<WHERE>##`     | 3 min     |
| 4min       |  14  | `*1*14*<WHERE>##`     | 4 min     |
| 5min       |  15  | `*1*15*<WHERE>##`     | 5 min     |
| 15min      |  16  | `*1*16*<WHERE>##`     | 15 min    |
| custom     |  —   | `*#1*<W>*#2*H*M*S##`  | Libera    |

Fonte: OpenWebNet WHO=1 v1.1, BTicino/Legrand, Nov 2014.

---

## Debug / Log

Aggiungi al `configuration.yaml` per log dettagliati:

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome_timer: debug
```

I log mostrano il frame OWN esatto inviato ad ogni chiamata.

---

## Compatibilità

- Home Assistant OS / Supervised
- MyHOME integration by anotherjulien, versione 0.8.6+
- Gateway BTicino Testati: MHS1
- 
