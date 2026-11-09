# -*- coding: utf-8 -*-
"""Writes src/data/rules.json (the default rules shipped with the tool).

Edit this file, run it, and commit both. Studio-specific rules do not go
here: they live in the data folder and are added from Classify.
"""
from __future__ import print_function, unicode_literals

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "src", "data", "rules.json")

BIM_IS = "BIM Ísland, CCI leiðbeiningar v2"
CCS = "Molio, CCS introduktion for arkitekter (2020)"
SUGG = "Tillaga verkfærisins / tool's suggestion - check"

rules = []


def r(rid, cats, code, note, verified=False, match=None, u=None, vv=None,
      topnode=None):
    rule = {"id": rid, "category": cats, "class": code, "note": note}
    if verified:
        rule["verified"] = True
    if match:
        rule["match"] = match
    if u:
        rule["u"] = u
        rule["vv"] = vv
    if topnode:
        rule["topnode"] = topnode
    rules.append(rule)


def names(*words):
    return {"name_contains": list(words)}


# ------------------------------------------------- specific (name) rules
D, W = ["OST_Doors"], ["OST_Windows"]
r("door_large", D, "QQE", CCS, True,
  names("bílskúrshurð", "iðnaðarhurð", "vöruhurð", "garage door",
        "overhead door", "sectional", "portdør", "industriport", "port"),
  "B", "AD")
r("door_gate", D, "QQF", CCS, True, names("hlið", "gate", "låge"))
r("door_hatch", D, "QQD", CCS, True,
  names("lúga", "hatch", "lem ", "luge"))
r("window_unit", W, "QQB", CCS, True,
  names("gluggaveggur", "gluggakerfi", "window wall", "vinduesparti",
        "vindueselement", "storefront"), "B", "AD")
r("handrail", ["OST_StairsRailing", "OST_Railings"], "FQC", CCS, True,
  names("handlisti", "handrail", "håndliste", "håndlist"))
# access control gates (security gates, speed gates) are gates: QQF Hlið
r("access_gate", ["OST_SecurityDevices", "OST_SpecialityEquipment",
                  "OST_GenericModel", "OST_Doors"], "QQF", SUGG, False,
  names("aðgangshlið", "hlið", "gate", "speedgate", "turnstile",
        "gunnebo", "acsctrl", "boarding"))
# a fence on the site (girðing) is RUA; guard rails stay FQD Handrið
r("fence", ["OST_Railings", "OST_Site"], "RUA", SUGG, False,
  names("girðing", "grindverk", "fence", "hegn", "skjólgirðing"))
r("tree", ["OST_Planting"], "TRA", SUGG, False,
  names("tré", "tree", "træ", "birki", "reynir", "ösp"))
r("smoke_damper", ["OST_DuctAccessory"], "FMB",
  "Molio: FMB = Røgspjæld / Flue damper. NB: BIM Ísland's examples use "
  "QMB for 'reykloka', but in Molio's table QMB is 'On-off spjæld' / "
  "'Gas shutoff valve'", False,
  names("reykloka", "smoke damper", "røgspjæld"))
r("shutoff_damper", ["OST_DuctAccessory"], "QMB", BIM_IS + " (QMB)", True,
  names("lokunarspjald", "on-off", "shutoff damper", "afspærringsspjæld"))
r("fire_damper", ["OST_DuctAccessory"], "FMA", SUGG, False,
  names("brunaloka", "eldvarnarloka", "fire damper", "brandspjæld"))
r("control_valve", ["OST_PipeAccessory"], "QNA", BIM_IS, True,
  names("stjórnloki", "stillliloki", "control valve", "reguleringsventil"))
r("shutoff_valve", ["OST_PipeAccessory"], "QMA", SUGG, False,
  names("lokunarloki", "kúluloki", "loki", "shutoff", "ball valve",
        "afspærring", "valve", "ventil"))
r("heat_exchanger", ["OST_MechanicalEquipment"], "EGC", BIM_IS, True,
  names("varmaskiptir", "heat exchanger", "varmeveksler"))
r("heat_pump", ["OST_MechanicalEquipment"], "EGA", SUGG, False,
  names("varmadæla", "heat pump", "varmepumpe"))
r("pump", ["OST_MechanicalEquipment"], "GPB", SUGG, False,
  names("dæla", "pump", "pumpe"))
r("fan", ["OST_MechanicalEquipment"], "GQB", SUGG, False,
  names("vifta", "blásari", "fan", "ventilator"))
r("radiator", ["OST_MechanicalEquipment", "OST_PlumbingFixtures"], "EPC",
  SUGG, False, names("ofn", "radiator", "varmepanel", "ofnar"))
# plumbing fixtures are often modelled as Generic Models or Specialty
# Equipment (manufacturer families), so the name rules look there too
P = ["OST_PlumbingFixtures", "OST_GenericModel", "OST_SpecialityEquipment"]
r("urinal", P, "XKC", SUGG, False, names("þvagskál", "urinal"))
r("toilet", P, "XKB", CCS, True,
  names("salerni", "klósett", "wc", "toilet"))
r("floor_drain", P, "XKE", CCS, True,
  names("niðurfall", "floor drain", "gulvafløb", "gólfniðurfall"))
r("sink", P, "XKA", CCS, True,
  names("vaskur", "handlaug", "sink", "basin", "lavatory", "vask"))
# Molio's table has no class for a shower or bath as such. The tray or tub
# collects waste water like a sink (XKA's definition: "collecting
# interfacing object of wastewater"); the mixer is a liquid control valve.
r("shower_mixer", P, "QNA", SUGG, False,
  names("sturtutæki", "blöndunartæki", "mixer", "armatur", "batteri"))
r("shower_bath", P, "XKA", SUGG, False,
  names("sturt", "shower", "bruse", "baðkar", "bathtub", "bath tub",
        "badekar"))

# rooms by name (Icelandic, English, Danish). Longer words first: the
# first rule that matches wins, and e.g. "stigagangur" contains "gangur".
SP = ["OST_Rooms", "OST_MEPSpaces"]
ROOMS = [
    # svalagangur (access balcony) is a corridor; other balconies and
    # terraces have no room class in Molio's table, so the group
    # "Occupiable space" (AA) is suggested
    ("access_balcony", "EAC", ["svalagang", "access balcony",
                               "altangang"]),
    ("balcony", "AA", ["svalir", "svölum", "balcony", "balkon", "altan",
                       "verönd", "terrace", "terrasse", "þaksvalir"]),
    ("sauna", "ABF", ["gufubað", "sauna"]),
    ("shower", "ABE", ["sturta", "sturtur", "shower", "bruserum"]),
    ("baby", "ABC", ["skiptiaðstaða", "skiptiherbergi", "baby"]),
    ("changing", "ABD", ["búningsherbergi", "búningsklefi", "búningsaðstaða",
                         "changing", "omklædning"]),
    ("bathroom", "ABA", ["baðherbergi", "bathroom", "badeværelse"]),
    ("toilet", "ABB", ["salerni", "snyrting", "wc", "toilet", "klósett"]),
    ("stairwell", "EAD", ["stigagangur", "stigahús", "stairwell", "stair",
                          "trapperum", "trappe"]),
    ("lift", "EAE", ["lyftuhús", "lyfta", "lift", "elevator", "elevatorskakt"]),
    ("shaft", "EBB", ["lagnastokkur", "lagnaskakt", "shaft", "skakt"]),
    ("airlock", "EAB", ["loftlás", "air lock", "airlock", "sluse",
                        "brunastúka", "brunaforstofa", "fire lobby"]),
    ("security", "BAK", ["ög stjórnun", "öryggisstjórn", "security control",
                         "öryggisstúka", "öryggisrými", "öryggisgæsla",
                         "vaktherbergi", "vaktstofa", "security", "guard"]),
    ("control", "DBA", ["stjórnstöð", "stjórnrými", "control room"]),
    ("cleaning", "CBB", ["ræstirými", "ræsting", "ræstiherbergi",
                         "ræstikompa", "rengøring", "janitor", "cleaning"]),
    ("cold_store", "CAG", ["frystir", "frystigeymsla", "kælir",
                           "kæligeymsla", "kælirými", "matvælageymsla",
                           "freezer", "cold room", "køle"]),
    ("dishwash", "BBA", ["uppvask", "uppþvott", "dishwash", "opvask"]),
    ("open_hall", "AA", ["blaðamann", "opið rými", "open hall"]),
    ("print", "BAA", ["prentrými", "prent", "ljósritun", "print", "copy"]),
    ("vestibule", "EAA", ["anddyri", "forstofa", "vindfang", "inngangur",
                          "entré", "vestibule", "lobby", "foyer"]),
    ("corridor", "EAC", ["gangur", "gangar", "corridor", "hallway", "gang"]),
    ("refuse", "CAA", ["sorpgeymsla", "sorp", "refuse", "waste", "affald",
                       "skraldespand"]),
    ("vehicles", "CBD", ["bílskúr", "bílageymsla", "hjólageymsla",
                         "bílakjallari", "bílastæði", "bílastæðahús",
                         "bílgeymsla", "vagnageymsla", "garage", "carport",
                         "parking", "parkering", "cykel", "bicycle"]),
    ("clothes", "CAK", ["fataherbergi", "fatahengi", "walk-in", "garderobe",
                        "wardrobe"]),
    ("electrical", "DAA", ["rafmagnstafla", "rafmagnsherbergi",
                           "rafmagnsrými", "töflurými", "el-rum", "elrum",
                           "electrical room", "switch room"]),
    ("it", "DAB", ["tölvurými", "netþjón", "server", "it-rum", "it room"]),
    ("sprinkler", "DAC", ["sprinkler", "úðakerfi", "úðarými",
                          "brunavatn", "sprinkler room"]),
    ("plant", "DAC", ["inntaksrými", "inntak", "lagnarými", "tæknirými",
                      "loftræsiklefi", "loftræsirými", "hitaklefi",
                      "plant room", "teknikrum", "teknik", "mechanical"]),
    ("sports", "BDA", ["íþróttasalur", "íþróttahús", "sports hall",
                       "idrætshal", "gym"]),
    ("meeting", "BAB", ["fundarherbergi", "fundarsalur", "fundur",
                        "meeting", "mødelokale", "møderum"]),
    ("reception", "BAC", ["móttaka", "afgreiðsla", "reception",
                          "modtagelse"]),
    ("teaching", "BAE", ["kennslustofa", "kennslurými", "classroom",
                         "undervisning", "klasselokale"]),
    ("study", "BAF", ["lesstofa", "lesrými", "study", "læsesal"]),
    ("office", "BAA", ["skrifstofa", "skrifstofur", "vinnurými", "office",
                       "kontor"]),
    ("laundry", "BAG", ["þvottahús", "þvottaherbergi", "þvottur",
                        "laundry", "vaskerum", "bryggers"]),
    ("treatment", "BAH", ["meðferðarherbergi", "meðferð", "treatment",
                          "behandling"]),
    ("kitchen", "BBA", ["eldhús", "kitchen", "køkken", "tekøkken"]),
    ("pantry", "BBA", ["kaffiaðstaða", "kaffistofa", "kaffi",
                       "tekøkken", "pantry", "kitchenette"]),
    ("studio", "BBD", ["vinnustofa", "studio", "atelier"]),
    ("dining", "BEA", ["borðstofa", "matsalur", "mötuneyti", "dining",
                       "spisestue", "kantine"]),
    ("waiting", "AAC", ["biðstofa", "biðrými", "waiting", "venterum"]),
    ("storage", "CAN", ["geymsla", "geymslur", "lager", "storage", "depot",
                        "stockroom", "opbevaring", "skur"]),
    ("living", "AAB", ["stofa", "alrými", "setustofa", "living",
                       "opholdsrum", "dagligstue", "stue"]),
    ("room", "AAA", ["svefnherbergi", "barnaherbergi", "herbergi",
                     "bedroom", "værelse", "soveværelse"]),
]
for rid, code, words in ROOMS:
    r("room_" + rid, SP, code, SUGG, False, names(*words))

# ---------------------------------------------- category defaults
r("curtain_wall", ["OST_Walls"], "QQB", SUGG + " (kerfisveggur = "
  "gluggaveggur / curtain wall = window unit)", False, {"curtain": True},
  "B", "AD")
r("wall", ["OST_Walls"], "AD", BIM_IS + "; " + CCS, True)
r("curtain_panel", ["OST_CurtainWallPanels"], "QQA", SUGG, False, None,
  "B", "AD")
r("mullion", ["OST_CurtainWallMullions"], "UND", SUGG)
r("window", W, "QQA", CCS, True, None, "B", "AD")
r("door", D, "QQC", BIM_IS + "; " + CCS, True, None, "B", "AD")
r("balcony", ["OST_Floors", "OST_GenericModel"], "AH", SUGG, False,
  names("svalir", "svala", "svalagólf", "svalaplata", "balcony", "balkon",
        "altan"))
r("floor", ["OST_Floors"], "AC", CCS, True)
r("ceiling", ["OST_Ceilings"], "NCD", CCS + " (loftklæðning)", True,
  None, "C", "AC")
r("roof", ["OST_Roofs"], "AE", CCS, True)
r("stair", ["OST_Stairs"], "AF", CCS, True)
r("stair_run", ["OST_StairsRuns"], "XSB", CCS, True)
r("stair_landing", ["OST_StairsLandings"], "XSA", CCS, True)
r("ramp", ["OST_Ramps"], "AG", CCS, True)
r("railing", ["OST_StairsRailing", "OST_Railings"], "FQD", CCS, True)
# manufacturer and in-house families modelled as Generic Models
GM = ["OST_GenericModel", "OST_SpecialityEquipment", "OST_Furniture",
      "OST_Casework"]
r("lift", ["OST_GenericModel", "OST_SpecialityEquipment"], "GMB", SUGG,
  False, names("lyfta", "lyftu", "elevator", "lift", "elevator"))
r("hatch_other", ["OST_GenericModel", "OST_SpecialityEquipment"], "QQD",
  SUGG, False, names("lúga", "hatch", "reyklúga"))
r("table", GM, "UBE", SUGG, False,
  names("borð", "table", "bord", "skrifborð", "desk"))
r("seat", GM, "CLC", SUGG, False,
  names("stóll", "stólar", "sófi", "bekkur", "chair", "sofa", "bench",
        "stol", "seat", "alford"))
r("dispenser", GM + ["OST_PlumbingFixtures"], "RB", SUGG, False,
  names("dispenser", "skammtari", "sápu", "pappírs", "handþurrk"))
r("ahu", ["OST_GenericModel", "OST_MechanicalEquipment"], "HF", SUGG,
  False, names("loftræstisamstæða", "loftræsti inntak", "loftinntak",
               "air handling", "ahu", "aggregat"))
r("casework", ["OST_Casework"], "RB", CCS, True)
r("furniture", ["OST_Furniture", "OST_FurnitureSystems"], "RB", CCS, True)
r("equipment", ["OST_SpecialityEquipment"], "RC", CCS, True)
r("planting", ["OST_Planting"], "RA", CCS, True)
r("hardscape", ["OST_Hardscape"], "AA", CCS, True)
r("column", ["OST_Columns", "OST_StructuralColumns"], "ULD",
  BIM_IS + "; " + CCS, True)
r("beam", ["OST_StructuralFraming"], "ULE", CCS, True)
r("foundation", ["OST_StructuralFoundation"], "AB", SUGG)
r("opening", ["OST_ShaftOpening", "OST_SWallRectOpening",
              "OST_FloorOpening", "OST_RoofOpening",
              "OST_StructuralFramingOpening", "OST_ColumnOpening"],
  "XTA", CCS, True)
r("luminaire", ["OST_LightingFixtures"], "UAC", BIM_IS, True, None,
  "K", "HH")
r("light_switch", ["OST_LightingDevices"], "SJA", SUGG, False, None,
  "K", "HH")
r("socket", ["OST_ElectricalFixtures"], "XDB", SUGG, False, None,
  "K", "JK")
r("cable_tray", ["OST_CableTray", "OST_CableTrayFitting"], "UBA", SUGG,
  False, None, "K", "JK")
r("duct", ["OST_DuctCurves", "OST_DuctFitting", "OST_FlexDuctCurves"],
  "WPB", SUGG, False, None, "J", "JJ")
r("air_terminal", ["OST_DuctTerminal"], "RND", SUGG, False, None,
  "J", "JJ")
r("insulation", ["OST_DuctInsulations", "OST_PipeInsulations"], "RQA",
  SUGG)
r("pipe", ["OST_PipeCurves", "OST_PipeFitting", "OST_FlexPipeCurves"],
  "WPA", CCS, True)

# a parking bay (Revit's Parking category) positions one vehicle
r("parking", ["OST_Parking"], "UAJ", SUGG)

# terrain: grass and planted ground is a vegetation area (CF), other
# terrain the subgrade (CA)
r("terrain_green", ["OST_Topography", "OST_Toposolid"], "CF", SUGG, False,
  names("gras", "grass", "gróður", "græn", "beð", "planting"))
r("terrain", ["OST_Topography", "OST_Toposolid"], "CA", SUGG)

# known categories without a default yet
for rid, cats in [
        ("site", ["OST_Site"]),
        ("generic", ["OST_GenericModel"]),
        ("entourage", ["OST_Entourage"]),
        ("conduit", ["OST_Conduit", "OST_ConduitFitting"]),
        ("electrical_equipment", ["OST_ElectricalEquipment"]),
        ("devices", ["OST_CommunicationDevices", "OST_DataDevices",
                     "OST_FireAlarmDevices", "OST_SecurityDevices",
                     "OST_NurseCallDevices", "OST_TelephoneDevices"]),
        ("mechanical_equipment", ["OST_MechanicalEquipment"]),
        ("duct_accessory", ["OST_DuctAccessory"]),
        ("pipe_accessory", ["OST_PipeAccessory"]),
        ("plumbing", ["OST_PlumbingFixtures"]),
        ("sprinkler", ["OST_Sprinklers"]),
        ("spaces", ["OST_Rooms", "OST_MEPSpaces"])]:
    r(rid, cats, None, "Enginn sjálfgefinn kóði / no default code")

data = {
    "_about": "Default mapping from Revit categories, family/type names and "
              "room names to CCI classes (Molio CCI 2020-05-26 R1 codes). "
              "Generated by tools/make_rules.py. 'verified': the code is "
              "shown for this use in BIM Ísland's or Molio's guides; others "
              "are the tool's suggestions. Studio rules go in the data "
              "folder, not here.",
    "table": "molio-cci-20200526-R1",
    "rules": rules,
}
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(data, ensure_ascii=False, indent=1))
print(len(rules), "rules ->", os.path.normpath(OUT))
