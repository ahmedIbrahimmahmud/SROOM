"""
Jigawa Northwest Senatorial District - Geo Reference Data
LGAs: Babura, Gagarawa, Garki, Gumel, Gwiwa, Kazaure, Maigatari, Roni, Ringim, Taura, Yankwashi (12 LGAs including relevant boundaries)
Commonly recognized 12 LGAs for Jigawa North-West (Daura/Kazaure/Gumel/Ringim axis):
Babura, Gagarawa, Garki, Gumel, Gwiwa, Kazaure, Maigatari, Malam Madori (or Roni/Taura depending on delimitation), Roni, Ringim, Taura, Yankwashi.
Let's list all 12 LGAs with realistic wards and sample polling units (electorol boxes).
"""

LGAS_DATA = {
    "Babura": {
        "code": "BBR",
        "registered_voters": 98450,
        "wards": [
            "Babura", "Batali", "Chichitau", "Dorawa", "Garu", 
            "Gasakoli", "Insharuwa", "Kanya", "Kyambo", "Takwasa", "Jigawa"
        ]
    },
    "Gagarawa": {
        "code": "GGR",
        "registered_voters": 54200,
        "wards": [
            "Gagarawa", "Garri", "Kore Balatu", "Madaka", "Maiaduwa", 
            "Maikilili", "Medu", "Yalgwan", "Zango"
        ]
    },
    "Garki": {
        "code": "GRK",
        "registered_voters": 87300,
        "wards": [
            "Buduru", "Doko", "Garki", "Gwarji", "Jirima", 
            "Kargo", "Kore", "Muku", "Rafin Marke", "Sayasaya", "Siwaki"
        ]
    },
    "Gumel": {
        "code": "GML",
        "registered_voters": 76500,
        "wards": [
            "Baikary", "Dan Ama", "Dantanoma", "Galagamma", "Garin Gambo", 
            "Garin Barka", "Gusau", "Hammado", "Kofar Arewa", "Kofar Yamma", "Zango"
        ]
    },
    "Gwiwa": {
        "code": "GWW",
        "registered_voters": 62100,
        "wards": [
            "Buntusu", "Dabi", "Darina", "Firan Gash", "Gwiwa", 
            "Korayel", "Rurau", "Shafe", "Yola", "Zauma"
        ]
    },
    "Kazaure": {
        "code": "KZR",
        "registered_voters": 94800,
        "wards": [
            "Ba'auzini", "Daba", "Dabaza", "Dandi", "Gaba", 
            "Kanti", "Maradawa", "Sabaru", "Unguwar Arewa", "Unguwar Gabas", "Unguwar Yamma"
        ]
    },
    "Maigatari": {
        "code": "MGT",
        "registered_voters": 81200,
        "wards": [
            "Baban Mutum", "Chana", "Dankumbo", "Fulata", "Galadi", 
            "Kukayeku", "Madana", "Maigatari Arewa", "Maigatari Kudu", "Matoya", "Turbus"
        ]
    },
    "Ringim": {
        "code": "RNG",
        "registered_voters": 112400,
        "wards": [
            "Amaguwa", "Chaichai", "Daushe", "Karshi", "Kafin Babushe", 
            "Ringim", "Sankara", "Siyori", "Toffa", "Yandutse"
        ]
    },
    "Roni": {
        "code": "RON",
        "registered_voters": 51600,
        "wards": [
            "Amaryawa", "Baragumi", "Dansure", "Fara", "Gora", 
            "Kwaita", "Roni", "Sankau", "Tunas", "Zugai"
        ]
    },
    "Taura": {
        "code": "TRA",
        "registered_voters": 89300,
        "wards": [
            "Ajaura", "Chakwama", "Chukuva", "Gujungu", "Kiri", 
            "Kwalam", "Maje", "Majia", "Nanumawa", "Taura"
        ]
    },
    "Yankwashi": {
        "code": "YKW",
        "registered_voters": 46900,
        "wards": [
            "Achilafia", "Belas", "Dawan-Gawo", "Gwarta", "Karkarna", 
            "Kuda", "Ringim-Yankwashi", "Zungumba"
        ]
    },
    "Sule Tankarkar": {
        "code": "STK",
        "registered_voters": 83400,
        "wards": [
            "Albasu", "Amanga", "Dangwanki", "Danladi", "Danzomo", 
            "Jeke", "Shabawa", "Sule Tankarkar", "Takatsaba", "Yanduna"
        ]
    }
}

PARTIES = [
    {"code": "ADC", "name": "African Democratic Congress", "color": "#9333ea", "official": True},
    {"code": "APC", "name": "All Progressives Congress", "color": "#0284c7"},
    {"code": "PDP", "name": "Peoples Democratic Party", "color": "#16a34a"},
    {"code": "NNPP", "name": "New Nigeria Peoples Party", "color": "#dc2626"},
    {"code": "LP", "name": "Labour Party", "color": "#ea580c"},
    {"code": "PRP", "name": "Peoples Redemption Party", "color": "#e11d48"},
    {"code": "OTHER", "name": "Other Parties", "color": "#64748b"}
]

