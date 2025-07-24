```
Vullingsgraad_dash/
├── app/
│   ├── app.py                      # Dash app
│   └── read.py                     # data readers
├── logs/
│   └── (log files go here)         # logging gaan we hier nog capturen
├── data/                           # all data files (input and output)
│   ├── mpn_locations.arrow         # locaties van H-Meetpunten
│   ├── peilgebieden_cso_combi.shp  # shape-file met peilgebieden
│   ├── vulling.arrow               # tijdseries met vulling (mm) per peilgebied
│   ├── vullingsgraad.arrow         # tijdseries met vullingsgraad (%) per peilgebied
│   ├── waterstand_meetpunt.arrow   # tijdseries met waterstand (m NAP) per H-meetpunt
│   ├── waterstand_pgb.arrow        # tijdseries met waterstand (m NAP) per peilgebied
├── tests/
│   └── (tests here)                # tests gaan we hier nog schrijven
├── README.md                      # project overview
└── .gitignore                     # git ignore rules
```