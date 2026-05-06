from __future__ import annotations

# NDC (National Destination Code) -> (municipality name, entity/region name)
# Used by import scripts and the CSV import API endpoint.
NDC_TO_MUNICIPALITY: dict[str, tuple[str, str]] = {
    # FBiH - fixed geographic
    "30": ("Mostar",         "Federacija Bosne i Hercegovine"),
    "31": ("Čapljina",       "Federacija Bosne i Hercegovine"),
    "32": ("Livno",          "Federacija Bosne i Hercegovine"),
    "33": ("Konjic",         "Federacija Bosne i Hercegovine"),
    "34": ("Zenica",         "Federacija Bosne i Hercegovine"),
    "35": ("Travnik",        "Federacija Bosne i Hercegovine"),
    "36": ("Sarajevo",       "Federacija Bosne i Hercegovine"),
    "37": ("Tuzla",          "Federacija Bosne i Hercegovine"),
    "38": ("Brčko",          "Brčko Distrikt"),
    "39": ("Bihać",          "Federacija Bosne i Hercegovine"),
    "49": ("Jablanica",      "Federacija Bosne i Hercegovine"),
    # RS - fixed geographic
    "50": ("Mrkonjić Grad",  "Republika Srpska"),
    "51": ("Banja Luka",     "Republika Srpska"),
    "52": ("Prijedor",       "Republika Srpska"),
    "53": ("Doboj",          "Republika Srpska"),
    "54": ("Šamac",          "Republika Srpska"),
    "55": ("Bijeljina",      "Republika Srpska"),
    "56": ("Zvornik",        "Republika Srpska"),
    "57": ("Istočno Sarajevo", "Republika Srpska"),
    "58": ("Foča",           "Republika Srpska"),
    "59": ("Trebinje",       "Republika Srpska"),
    # Mobile (nationwide, mapped to FBiH region for organisational purposes)
    "63": ("HT Mobilni",     "Federacija Bosne i Hercegovine"),
    "64": ("HT Mobilni",     "Federacija Bosne i Hercegovine"),
}
