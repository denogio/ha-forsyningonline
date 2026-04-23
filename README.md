# ForsyningOnline Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![License](https://img.shields.io/github/license/forsyningonline/ha-forsyningonline)
![Version](https://img.shields.io/badge/version-0.1.0-green)
![HA Version](https://img.shields.io/badge/HA-2026.4%2B-blue)

Home Assistant integration til [ForsyningOnline.dk](https://forsyningonline.dk) der henter vandforbrugsdata.

## Features

- 💧 **HA Energy kompatibel** - Virker med Home Assistant Energy dashboard
- 📊 **Korrekt timefordeling** - Historisk timedata importeres med korrekte timestamps
- 🏠 **Flere lokationer** - Understøtter flere vandværk/adresser
- ⚙️ **Konfigurerbart** - Juster opdateringsinterval via options

## Sensors

| Entity | Beskrivelse | HA Energy |
|--------|-------------|-----------|
| `sensor.<lokation>_water_total` | Samlet vandforbrug (m³) | ✓ |
| `sensor.<lokation>_water_today` | Dagens vandforbrug (m³) | |

Timedata importeres automatisk som HA statistik, så Energy dashboardet viser forbrug fordelt på de korrekte timer — selvom data fra API'et er forsinket.

## Installation

### Via HACS (Anbefalet)

1. Åbn HACS i Home Assistant
2. Gå til "Integrations"
3. Klik på de tre prikker → "Custom repositories"
4. Tilføj dette repository
5. Klik på "ForsyningOnline" → "Download"
6. Restart Home Assistant

### Manuel

1. Download den seneste [release](../../releases)
2. Pak indholdet ud i `custom_components/forsyningonline/`
3. Restart Home Assistant

## Opsætning

1. Gå til **Settings** → **Devices & Services**
2. Klik **Add Integration**
3. Søg efter "ForsyningOnline"
4. Indtast dit ForsyningOnline brugernavn og kodeord
5. Vælg din lokation (hvis du har flere)

## Brug med HA Energy

For at tilføje vandforbrug til dit Energy dashboard:

1. Gå til **Energy** dashboardet
2. Klik på **Menu** → **Energy**
3. Under "Water consumption" → **Add consumption**
4. Vælg `sensor.<lokation>_water_total`

## Fejlsøgning

### Login virker ikke
- Tjek at du bruger det korrekte brugernavn (ofte 10-cifret)
- Prøv at logge ind på forsyningonline.dk i browser for at bekræfte credentials

### Ingen data efter opsætning
- Vent på første data opdatering (op til 1 time)
- Data fra ForsyningOnline API'et kan være forsinket med flere timer
- Check "Developer Tools" → "States" for at se sensor-værdier
- Tjek HA logs for fejl

## License

MIT License - se [LICENSE](LICENSE) filen.

---
<sub>Built with AI assistance</sub>
