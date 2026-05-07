from __future__ import annotations

# NDC (National Destination Code) -> (municipality/cantonal-capital name, entity/region name)
# Source: RAK Plan brojeva za telefonske usluge u BiH (primjena od 01.10.2017.)
# FBiH NDCs correspond to cantons; municipality name = cantonal capital.
NDC_TO_MUNICIPALITY: dict[str, tuple[str, str]] = {
    # FBiH - fiksni geografski (NDC = kantonski kod)
    "30": ("Travnik",           "Federacija Bosne i Hercegovine"),  # Središnjobosanska županija
    "31": ("Orašje",            "Federacija Bosne i Hercegovine"),  # Posavska županija
    "32": ("Zenica",            "Federacija Bosne i Hercegovine"),  # Zeničko-dobojska županija
    "33": ("Sarajevo",          "Federacija Bosne i Hercegovine"),  # Kanton Sarajevo
    "34": ("Livno",             "Federacija Bosne i Hercegovine"),  # Hercegbosanska županija
    "35": ("Tuzla",             "Federacija Bosne i Hercegovine"),  # Tuzlanska županija
    "36": ("Mostar",            "Federacija Bosne i Hercegovine"),  # Hercegovačko-neretvanska županija
    "37": ("Bihać",             "Federacija Bosne i Hercegovine"),  # Unsko-sanska županija
    "38": ("Goražde",           "Federacija Bosne i Hercegovine"),  # Bosansko-podrinjska županija
    "39": ("Grude",             "Federacija Bosne i Hercegovine"),  # Zapadnohercegovačka županija
    "49": ("Brčko",             "Brčko Distrikt"),                  # Brčko Distrikt BiH
    # RS - fiksni geografski
    "50": ("Mrkonjić Grad",     "Republika Srpska"),
    "51": ("Banja Luka",        "Republika Srpska"),
    "52": ("Prijedor",          "Republika Srpska"),
    "53": ("Doboj",             "Republika Srpska"),
    "54": ("Šamac",             "Republika Srpska"),
    "55": ("Bijeljina",         "Republika Srpska"),
    "56": ("Zvornik",           "Republika Srpska"),
    "57": ("Istočno Sarajevo",  "Republika Srpska"),
    "58": ("Foča",              "Republika Srpska"),
    "59": ("Trebinje",          "Republika Srpska"),
    # Mobilni - nije geografski, organizacijski pridružen FBiH
    "63": ("HT Mobilni",        "Federacija Bosne i Hercegovine"),
    "64": ("HT Mobilni",        "Federacija Bosne i Hercegovine"),
}
