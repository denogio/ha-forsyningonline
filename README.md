# ForsyningOnline Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![License](https://img.shields.io/github/license/denogio/ha-forsyningonline)
![Version](https://img.shields.io/badge/version-0.2.5-green)
![HA Version](https://img.shields.io/badge/HA-2026.4%2B-blue)

Home Assistant integration til [ForsyningOnline.dk](https://forsyningonline.dk) der henter vandforbrugsdata.

## Features

- 💧 **HA Energy kompatibel** - Virker med Home Assistant Energy dashboard
- 📊 **Korrekt timefordeling** - Historisk timedata importeres med korrekte timestamps
- 📅 **Konfigurerbar historik** - Importer fra 7 dage til al tilgængelig data
- 🏠 **Flere lokationer** - Understøtter flere vandværk/adresser
- ⚙️ **Konfigurerbart** - Juster opdateringsinterval og historikdybde via options

## Sensors

| Entity | Beskrivelse |
|--------|-------------|
| `sensor.<lokation>_water_total` | Samlet vandforbrug (m³) |
| `sensor.<lokation>_water_today` | Dagens vandforbrug (m³) |

Timedata importeres automatisk som ekstern HA statistik (`forsyningonline:water_consumption_...`), så Energy dashboardet viser forbrug fordelt på de korrekte timer — selvom data fra API'et er forsinket.

## Installation

### Via HACS (Anbefalet)

1. Åbn HACS i Home Assistant
2. Gå til "Integrations"
3. Klik på de tre prikker (⋮) → "Custom repositories"
4. Indsæt repository URL:
   ```
   https://github.com/denogio/ha-forsyningonline
   ```
5. Vælg kategori: **Integration**
6. Klik "Add"
7. Find "ForsyningOnline" i listen → klik "Download"
8. Restart Home Assistant

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
4. Vælg statistikken `forsyningonline:water_consumption_...`

> **Bemærk:** Vælg den eksterne statistik — ikke sensor-entiteten. Statistikken indeholder korrekt timefordelt data.

## Indstillinger

Under integrationsindstillinger (Options) kan du justere:

| Indstilling | Beskrivelse | Standard |
|-------------|-------------|----------|
| Opdateringsinterval | Hvor ofte der hentes nye data (sekunder) | 3600 (1 time) |
| Historisk dataimport | Hvor langt tilbage der importeres ved opstart | 30 dage |

Valgmuligheder for historisk import: 7 dage, 30 dage, 3 måneder, 6 måneder, 1 år, eller al tilgængelig data.

## Fejlsøgning

### Login virker ikke
- Tjek at du bruger det korrekte brugernavn (ofte 10-cifret)
- Prøv at logge ind på forsyningonline.dk i browser for at bekræfte credentials

### Ingen data efter opsætning
- Vent på første data opdatering (op til 1 time)
- Data fra ForsyningOnline API'et kan være forsinket med flere timer
- Check "Developer Tools" → "Statistics" for at se importeret data
- Tjek HA logs for fejl

### Forbrug vises ikke i Energy dashboard
- Sørg for at vælge den eksterne statistik (`forsyningonline:water_consumption_...`), ikke sensor-entiteten
- Tjek under "Developer Tools" → "Statistics" at data er importeret

## License

MIT License - se [LICENSE](LICENSE) filen.

---
<sub>Built with AI assistance</sub>
