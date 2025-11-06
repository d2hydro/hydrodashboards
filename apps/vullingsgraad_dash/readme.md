# 🌊 Vullingsgraad Dash App

Een interactieve webapplicatie voor het visualiseren van **vullingsgraad**, **vulling**, en **waterstand** per peilgebied.  
De applicatie is gebouwd in **[Plotly Dash](https://dash.plotly.com)** en vervangt een eerdere implementatie in **Bokeh**.

---

## Overzicht

De app combineert:
- een **kaartcomponent** voor geografische selectie van peilgebieden,
- een **tijdbalk en animatie** om de tijdreeksen te verkennen,
- en een **gecombineerde grafiek** met dynamische tijdlijn (marker).

Alle onderdelen zijn modulair opgebouwd en communiceren via **Dash callbacks**.

---

## Architectuur & Modulariteit
vullingsgraad_dash/
│
├── app.py # Hoofdapplicatie: init, layout en callback-registratie
│
├── components/ # UI-componenten (elk met eigen callbacks)
│ ├── map/ # Interactieve kaartlagen en selectie
│ ├── combined_graph/ # 📊 Tijdreeksen met tijdlijn en subplots
│ ├── video_graph/ # 🎬 Tijdslider, mini-grafiek en animatie
│ └── share_url.py # 🔗 Deelbare URL's en status-synchronisatie
│
├── utils/ # Hulpfuncties en stijlen
│ ├── data_loader.py # Data laden & caching
│ ├── map_utils.py # Kaartkleuren en stijlberekeningen
│ ├── readers.py # Bestandslezers (CSV, Parquet, GeoJSON)
│ ├── style.py # Layout & kleurenschema’s
│ └── generate_styles.py # Automatisch CSS genereren in /assets
│
└── assets/ #  Front-end CSS & JS
├── reset_margins.css
├── page_loader.css
├── share_url.css
├── dashExtensions_default.js
└── favicon.ico

### 🔹 Lagenstructuur
| Laag | Verantwoordelijkheid |
|------|----------------------|
| **Regielaag** | `app.py` – initialiseert, laadt data en koppelt modules |
| **Componentenlaag** | `map/`, `combined_graph/`, `video_graph/`, `share_url.py` – UI en callbacks |
| **Hulplaag** | `utils/` – data, stijlen en hulpmethodes (geen callbacks) |
| **Presentatielaag** | `assets/` – visuele opmaak in CSS/JS |

---

## ⚙Belangrijkste modules

| Module | Functie |
|--------|---------|
| **TimeMarker** | Beheert de verticale tijdlijn in de grafieken, beweegt mee met zoom en slider |
| **CombinedGraphFigure** | Bouwt de drie subplots voor vullingsgraad, vulling en waterstand |
| **MapController** | Stuurt kaartlagen, selectie en kleurupdates aan |
| **TimeControls** | Bevat tijdslider, mini-grafiek en animatielogica |
| **ShareURL** | Zorgt dat de huidige selectie via URL deelbaar is |
| **DataLoader** | Laadt datasets en bereidt standaardselecties voor |

---

## Waarom overgestapt van *Bokeh* naar *Dash*

| Aspect | Bokeh | Dash |
|---------|--------|------|
| **Interactiviteit** | Sterk maar complex bij koppeling tussen views | Natuurlijke callback-architectuur |
| **Webintegratie** | Vereist extra server of embedding | Volledig web-native via Flask |
| **UI-samenstelling** | Minder flexibel voor samengestelde dashboards | Component-based en modulair |
| **Community & support** | Kleiner ecosysteem | Groot ecosysteem & Plotly integratie |
| **Leercurve** | Steile leercurve bij callbacks | Eenduidige declaratieve structuur |

*Conclusie:* Dash biedt meer modulariteit, eenvoudiger beheer van callbacks en een soepelere integratie van kaart en grafieken in één webapplicatie.

---

## Runnen van de app



# 3️⃣ Open in browser
http://127.0.0.1:5005
