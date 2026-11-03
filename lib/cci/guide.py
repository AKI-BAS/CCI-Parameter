# -*- coding: utf-8 -*-
"""Content of the Guide window (Leiðbeiningar), in Icelandic and English.

Pages are lists of simple blocks so the same content can be shown in WPF,
tested, or printed:

    {"t": "h2"|"h3"|"p"|"note"|"warn"|"code", "text": "..."}
    {"t": "ul"|"ol", "items": ["...", ...]}
    {"t": "table", "head": [...], "rows": [[...], ...]}

Inline markup in text: **bold** and `code`.

Tables are built from the tool's own data (parameters, scopes, LOD
groups, topnodes, check messages), so the guide stays right when those
change. Sources: BIM Ísland, CCI leiðbeiningar v2 (2023) and CCI
leiðbeiningar fyrir Revit (2023); DiKon/BIM7AA/Molio, Þróunarstig
byggingarhluta REV4 (BIM Ísland translation, 2022); Molio, CCS
introduktion for arkitekter (2020).
"""
from __future__ import unicode_literals

import re

from cci import formats, groups
from cci.i18n import t

LANG = ["en"]


def L(is_text, en_text):
    return is_text if LANG[0] == "is" else en_text


def h2(text):
    return {"t": "h2", "text": text}


def h3(text):
    return {"t": "h3", "text": text}


def p(text):
    return {"t": "p", "text": text}


def note(text):
    return {"t": "note", "text": text}


def warn(text):
    return {"t": "warn", "text": text}


def code(text):
    return {"t": "code", "text": text}


def ul(*items):
    return {"t": "ul", "items": list(items)}


def ol(*items):
    return {"t": "ol", "items": list(items)}


def table(head, rows):
    return {"t": "table", "head": list(head), "rows": [list(r) for r in rows]}


def btn(name):
    """Button name as shown on the ribbon, on one line."""
    return t("btn.%s.title" % name).replace("\n", " ")


# ------------------------------------------------------------------ pages

def page_steps():
    b = [
        h2(L("Skref fyrir skref", "Step by step")),
        p(L("Svona er líkan CCI flokkað frá upphafi til skila. Fylgdu "
            "skrefunum í þessari röð. Hnapparnir eru á flipanum **CCI**. "
            "Hnappurinn **Staða líkansins** hér fyrir neðan sýnir hvað er "
            "þegar búið í opna líkaninu.",
            "This is how a model is CCI-classified from start to delivery. "
            "Follow the steps in this order. The buttons are on the **CCI** "
            "tab. The **Model status** button below shows what is already "
            "done in the open model.")),
        h3(L("0. Áður en þú byrjar", "0. Before you start")),
        ul(L("Finndu út hvað verkkaupi krefst: hvaða **umfang** kóðunar "
             "(sjá flipann Umfang) og hvaða **þróunarstig** (LOD) á að "
             "skila. Það stendur yfirleitt í BIM-áætlun eða skilakröfum.",
             "Find out what the client requires: which **scope** of coding "
             "(see the Scope tab) and which **level of development** (LOD) "
             "to deliver. It is usually in the BIM execution plan or "
             "delivery requirements."),
           L("Vistaðu afrit af líkaninu, eða vinndu í miðlægu líkani svo "
             "hægt sé að fara til baka.",
             "Save a copy of the model, or work in a central model, so you "
             "can go back."),
           L("Allt sem verkfærið skrifar er í einu Undo skrefi á hnapp.",
             "Everything a button writes is one Undo step.")),
    ]
    steps = [
        ("setup",
         L("Hakaðu við umfangið sem verkkaupi biður um. Settu númer "
           "byggingar og hæðakóða (01 = 1. hæð, K1 = kjallari, M2 = "
           "millihæð). Settu þróunarstig á hvern byggingarhluta.",
           "Tick the scope the client asks for. Set the building number "
           "and storey codes (01 = 1st floor, K1 = basement, M2 = "
           "mezzanine). Set the LOD for each element group."),
         L("Stillingarnar vistast í líkaninu, svo allir sem vinna í því "
           "nota þær sömu.",
           "The settings are saved in the model, so everyone working in it "
           "uses the same ones."),
         L("Hæðir án kóða fá engin rýmisnúmer. Millihæðir þarf að setja "
           "handvirkt.",
           "Levels without a code get no room numbers. Mezzanines must be "
           "set by hand.")),
        ("table",
         L("Yfirleitt ekkert. Opnaðu hann til að sjá hvaða útgáfa CCI "
           "töflunnar er í notkun, eða til að lesa inn nýrri útgáfu frá "
           "Molio.",
           "Usually nothing. Open it to see which edition of the CCI table "
           "is in use, or to load a newer one from Molio."),
         L("Upplýsingar um töfluna og hvort kóðar í líkaninu vanti í hana.",
           "Information about the table, and whether codes in the model "
           "are missing from it."),
         L("Ný tafla er aldrei tekin í notkun án þess að þú sjáir fyrst "
           "hvað breytist.",
           "A new table is never used without first showing you what "
           "changes.")),
        ("params",
         L("Aðeins ef líkanið hefur ekki CCI eigindin. Veldu skrá Molio ef "
           "stofan hefur hana, annars skrá verkfærisins. Ef líkanið hefur "
           "þau þegar (úr sniðmáti) skaltu frekar velja **Vista skrá úr "
           "þessu verkefni** og nota hana í önnur verkefni.",
           "Only if the model doesn't have the CCI parameters. Pick Molio's "
           "file if the studio has it, otherwise the tool's own file. If "
           "the model already has them (from a template), choose **Save "
           "the file from this project** instead and use it for other "
           "projects."),
         L("Eigindin birtast undir Identity Data á réttum flokkum.",
           "The parameters appear under Identity Data on the right "
           "categories."),
         L("'Árekstur' þýðir að til er eigindi með sama nafni sem er ekki "
           "shared parameter. Fjarlægðu það í Manage > Project Parameters.",
           "'Conflict' means a parameter with the same name exists that is "
           "not a shared parameter. Remove it in Manage > Project "
           "Parameters.")),
        ("classify",
         L("Farðu yfir listann: ein lína fyrir hverja tegund og hvert "
           "rýmisheiti. Dálkurinn **Núna** sýnir það sem er í líkaninu, "
           "**Tillaga** og **Heimild** hvað verkfærið leggur til og hvaðan. "
           "Breyttu dálkinum **Flokkun** þar sem þarf, eða notaðu **Velja "
           "úr töflu**. Ef líkanið hefur eldri kóðun: **Skipta út eldri "
           "kóðun**.",
           "Go through the list: one row per type and per room name. The "
           "**Now** column shows what is in the model, **Suggestion** and "
           "**Source** what the tool suggests and why. Edit the **Class** "
           "column where needed, or use **Pick from table**. If the model "
           "has old coding: **Replace old coding**."),
         L("Flokkun, klasi og CCIClassification eru skrifuð á tegundirnar "
           "(og afrituð á hlutina).",
           "Class, topnode and CCIClassification are written to the types "
           "(and copied to the elements)."),
         L("Línur án tillögu: veldu kóða úr töflunni og hakaðu við "
           "**Muna**, þá verður hann lagður til næst.",
           "Rows without a suggestion: pick a code from the table and tick "
           "**Remember**, so it is suggested next time.")),
        ("number",
         L("Smelltu eftir að flokkun er lokið. Verkfærið gefur hverri "
           "tegund tegundarauðkenni (%QQC001) og, eftir umfangi, hverjum "
           "hlut vöruauðkenni (#QQC001).",
           "Click after classifying. The tool gives each type a type ID "
           "(%QQC001) and, depending on scope, each element a product ID "
           "(#QQC001)."),
         L("Númer breytast aldrei eftir þetta og eru aldrei endurnýtt, "
           "svo óhætt er að keyra aftur.",
           "Numbers never change after this and are never reused, so it is "
           "safe to run again."),
         L("'Engin flokkun' þýðir að Flokka hefur ekki verið keyrt á "
           "þessar tegundir.",
           "'No classification' means Classify has not been run on those "
           "types.")),
        ("locations",
         L("Aðeins ef umfangið er Rekstur eða Staðsetningarauðkenni. Rýmin "
           "þurfa númer og hæðirnar kóða.",
           "Only if the scope includes Operations or Location ID. Rooms "
           "need numbers and levels need codes."),
         L("Rými fá B01.01.001, hurðir og búnaður +B01.01.001 (rýmið sem "
           "þau eru í).",
           "Rooms get B01.01.001, doors and equipment +B01.01.001 (the room "
           "they are in)."),
         L("Veggir og gólf ná yfir mörg rými og fá ekki staðsetningu; það "
           "er rétt.",
           "Walls and floors span several rooms and get no location; that "
           "is correct.")),
        ("check",
         L("Keyrðu oft. Lestu fyrst **Yfirlit flokkunar**: er hver flokkur "
           "með þann kóða sem þú býst við? Lagaðu svo villurnar.",
           "Run it often. Read the **Classification overview** first: does "
           "each category have the code you expect? Then fix the errors."),
         L("Villur (þarf að laga), viðvaranir (athugaðu) og ábendingar. "
           "Hægt að vista sem CSV.",
           "Errors (must fix), warnings (check) and notes. Can be saved as "
           "CSV."),
         L("Flipinn **Algeng vandamál** útskýrir hverja athugasemd.",
           "The **Common problems** tab explains every finding.")),
        ("ifc",
         L("Áður en IFC er flutt út: vistaðu skrána og settu gildin inn í "
           "IFC export stillingar Revit eins og hnappurinn sýnir.",
           "Before exporting IFC: save the file and enter the values in "
           "Revit's IFC export settings as the button shows."),
         L("CCI eigindin fara í eigindasafnið CCI_Administrative í IFC.",
           "The CCI parameters go into the CCI_Administrative property set "
           "in the IFC."),
         L("Opnaðu IFC skrána í ACC (Autodesk Construction Cloud) og athugaðu "
           "nokkra hluti.",
           "Open the IFC in ACC (Autodesk Construction Cloud) and check a "
           "few elements.")),
    ]
    for i, (name, what, result, trouble) in enumerate(steps):
        b.append(h3("%d. %s" % (i + 1, btn(name))))
        b.append(p(what))
        b.append(ul(L("**Útkoma:** ", "**Result:** ") + result,
                    L("**Ef eitthvað fer úrskeiðis:** ",
                      "**If something goes wrong:** ") + trouble))
    b.append(note(L("Þegar líkanið breytist (nýjar tegundir, ný rými): "
                    "keyrðu Flokka, Númera, Staðsetningu og Athuga aftur. "
                    "Það sem er þegar rétt helst óbreytt.",
                    "When the model changes (new types, new rooms): run "
                    "Classify, Number, Locations and Check again. What is "
                    "already right stays as it is.")))
    return b


def page_cci(ct=None):
    b = [
        h2(L("Hvað er CCI?", "What is CCI?")),
        p(L("CCI (Construction Classification International) er "
            "flokkunarkerfi fyrir mannvirki. BIM Ísland mælir með því á "
            "Íslandi. Það uppfyllir ISO 12006 og ISO/IEC 81346, er gjaldfrjálst "
            "og byggir á sama grunni og KKS kerfið sem notað hefur verið í "
            "orkuverum á Íslandi. Molio í Danmörku heldur töflunum við.",
            "CCI (Construction Classification International) is a "
            "classification system for construction. BIM Ísland recommends "
            "it in Iceland. It follows ISO 12006 and ISO/IEC 81346, is free, "
            "and shares its basis with the KKS system long used in Icelandic "
            "power plants. Molio in Denmark maintains the tables.")),
        h3(L("Flokkun eftir virkni", "Classified by function")),
        p(L("CCI flokkar hluti eftir **eðlislægri virkni** þeirra, ekki "
            "efni eða útliti. Stálhurð og timburhurð eru báðar **QQC** "
            "(hurð): aðgangshluti fyrir fólk. Gluggi er **QQA**: aðgangshluti "
            "fyrir birtu. Munurinn á tveimur hurðum kemur fram í "
            "tegundarauðkenninu, ekki flokkuninni.",
            "CCI classifies things by their **inherent function**, not "
            "material or looks. A steel door and a timber door are both "
            "**QQC** (door): an access object for people. A window is "
            "**QQA**: an access object for light. The difference between "
            "two doors shows in the type ID, not the class.")),
        h3(L("Flokkun og auðkenni", "Classification and identification")),
        table([L("Spurning", "Question"), L("Svar í CCI", "CCI answer"),
               L("Dæmi", "Example")], [
            [L("Hvað er þetta?", "What is it?"),
             L("Flokkun", "Classification"), "QQC (" +
             L("hurð", "door") + ")"],
            [L("Hvaða gerð?", "Which kind?"),
             L("Tegundarauðkenni", "Type ID"), "%QQC001"],
            [L("Hvaða eintak?", "Which one?"),
             L("Vöruauðkenni", "Product ID"), "#QQC123"],
            [L("Hvar er það?", "Where is it?"),
             L("Staðsetningarauðkenni", "Location ID"), "+B01.01.101"],
            [L("Í hvaða kerfi?", "In which system?"),
             L("Kerfisauðkenni", "Function ID"), "=H01.HD02.EGC001"],
        ]),
        h3(L("Þrjú stig byggingarhluta", "Three levels of building "
             "elements")),
        p(L("Byggingarhlutar [L] eru flokkaðir á þremur stigum. Fjöldi "
            "bókstafa segir á hvaða stigi kóðinn er:",
            "Building elements [L] are classified at three levels. The "
            "number of letters tells you the level:")),
        table([L("Stig", "Level"), L("Stafir", "Letters"),
               L("Dæmi", "Example"), L("Notað fyrir", "Used for")], [
            [L("Virknikerfi", "Functional system"), "1", "B " +
             L("Veggir", "Walls"),
             L("Forhönnun, skipulag kerfa", "Early design, system layout")],
            [L("Tæknikerfi", "Technical system"), "2", "AD " +
             L("Vegguppbygging", "Wall construction"),
             L("Uppbyggingar: veggir, gólf, þök", "Build-ups: walls, "
               "floors, roofs")],
            [L("Byggingarhluti", "Component"), "3", "QQC " +
             L("Hurð", "Door"),
             L("Stakir hlutir: hurðir, gluggar, súlur", "Single objects: "
               "doors, windows, columns")],
        ]),
        p(L("Saman mynda þau samsett tegundarauðkenni: **§B.AD.QQC001** = "
            "hurð (QQC), tegund 1, í vegguppbyggingu (AD) í veggjakerfi (B).",
            "Together they form the multi-level type ID: **§B.AD.QQC001** = "
            "door (QQC), type 1, in a wall construction (AD) in the wall "
            "system (B).")),
        p(L("Hver stafur þrengir flokkinn. Dæmi um byggingarhluta:",
            "Each letter narrows the class. Example for a component:")),
    ]
    chain = [("Q", L("Opnanlegir og stýrandi hlutar", "Controlling object")),
             ("QQ", L("Gluggar, hurðir og op", "Space access object")),
             ("QQC", L("Hurð", "Door"))]
    if ct is not None:
        chain = [("Q", ct.group_name("component", "Q", LANG[0]) or
                  chain[0][1]),
                 ("QQ", ct.group_name("component", "QQ", LANG[0]) or
                  chain[1][1]),
                 ("QQC", ct.name("QQC", LANG[0], "[L]") or chain[2][1])]
    b.append(ul(*["`%s` %s" % c for c in chain]))
    b += [
        note(L("Arkitektar flokka yfirleitt uppbyggingar sem tæknikerfi "
               "(veggir AD, gólf AC, þök AE) og stakar einingar sem "
               "byggingarhluta (gluggar QQA, hurðir QQC). Burðarþolshönnuðir "
               "nota t.d. BD fyrir burðarvirki veggja. Flokkaðu ekki "
               "nákvæmar en þú teiknar: gifsveggur er AD, ekki hver "
               "gifsplata.",
               "Architects usually classify build-ups as technical systems "
               "(walls AD, floors AC, roofs AE) and single units as "
               "components (windows QQA, doors QQC). Structural engineers "
               "use e.g. BD for wall structures. Don't classify in more "
               "detail than you model: a plasterboard wall is AD, not each "
               "board.")),
        h3(L("Klasar (topnodes)", "Domains (topnodes)")),
        p(L("Sami bókstafakóði getur þýtt ólíka hluti eftir klasa, svo "
            "klasinn er skráður sérstaklega í **CCITopnode**. Byggingarhlutar "
            "eru [L], rými [B] eða [A].",
            "The same letters can mean different things in different "
            "domains, so the domain is stored separately in "
            "**CCITopnode**. Building elements are [L], spaces [B] or [A].")),
        table([L("Klasi", "Domain"), L("Heiti", "Name")],
              [["[%s]" % tn, t("topnode." + tn)]
               for tn in formats.TOPNODES]),
    ]
    return b


PARAM_SPECS = [
    # key, prefix, format, example, applies (kind keys)
    ("class", "", "X / XX / XXX", "QQC, AD"),
    ("topnode", "[ ]", "[X]", "[L], [B]"),
    ("type_id", "%", "%XXXaaa", "%QQC001"),
    ("ml_type_id", "§", "§U.VV.XXXbbb", "§B.AD.QQC001"),
    ("single_id", "#", "#XXXccc", "#QQC001"),
    ("functional_id", "=", "=Ukk.VVmm.XXXppp", "=H01.HD02.EGC001"),
    ("ml_location_id", "", "Bxx.yy.zzz", "B01.01.001"),
    ("location_at_id", "+", "+Bxx.yy.zzz", "+B01.01.101"),
    ("classification", "", "XXX:Name", "QQC:Door"),
]


def _applies(key):
    kinds = [k for k, keys in groups.PARAMS_BY_KIND.items() if key in keys]
    names = {"element": L("byggingarhlutar", "building elements"),
             "system": L("lagnir og búnaður", "MEP elements"),
             "space": L("rými", "spaces")}
    order = ["element", "system", "space"]
    return ", ".join(names[k] for k in order if k in kinds)


def page_params():
    rows = []
    for key, prefix, fmt, example in PARAM_SPECS:
        name = formats.PARAM[key]
        if key + "_t" in formats.PARAM:
            name += " / " + formats.PARAM[key + "_t"]
        rows.append([name, prefix or "-", fmt, example, _applies(key)])
    b = [
        h2(L("Eigindi og gildi", "Parameters and values")),
        p(L("Þetta eru CCI eigindin úr leiðbeiningum BIM Íslands, hvernig "
            "gildin eiga að líta út og á hvaða hluti þau fara.",
            "These are the CCI parameters from BIM Ísland's guidelines, what "
            "the values should look like and which elements they go on.")),
        table([L("Eigindi", "Parameter"), L("Forskeyti", "Prefix"),
               L("Snið", "Format"), L("Dæmi", "Example"),
               L("Á", "On")], rows),
        h3(L("Hvað þýða stafirnir í sniðinu?", "What the letters in the "
             "format mean")),
        ul(L("**X, XX, XXX**: flokkunarkóði, 1-3 hástafir.",
             "**X, XX, XXX**: class code, 1-3 capital letters."),
           L("**aaa, ccc**: hlaupandi númer, t.d. 001.",
             "**aaa, ccc**: running number, e.g. 001."),
           L("**U, VV**: virknikerfi (1 stafur) og tæknikerfi (2 stafir).",
             "**U, VV**: functional system (1 letter) and technical system "
             "(2 letters)."),
           L("**xx.yy.zzz**: bygging, hæð, rými. Hæð: 01 = 1. hæð, K1 = "
             "fyrsta kjallarahæð, M2 = millihæð ofan 2. hæðar.",
             "**xx.yy.zzz**: building, storey, room. Storey: 01 = 1st "
             "floor, K1 = first basement, M2 = mezzanine above the 2nd "
             "floor.")),
        h3(L("Af hverju [Type] á eftir nafninu?", "Why [Type] after the "
             "name?")),
        p(L("Hvert gildi getur verið á tegundinni (`CCIClassCode[Type]`) og "
            "á einstökum hlut (`CCIClassCode`). Revit leyfir ekki tvö eigindi "
            "með sama nafni, svo BIM Ísland setur [Type] á tegundareigindið. "
            "Í Type Properties sérðu því aðeins [Type] eigindi.",
            "Each value can live on the type (`CCIClassCode[Type]`) and on a "
            "single element (`CCIClassCode`). Revit doesn't allow two "
            "parameters with the same name, so BIM Ísland adds [Type] to the "
            "type parameter. In Type Properties you therefore only see "
            "[Type] parameters.")),
        note(L("**Instance gildi gengur alltaf framar tegund.** Ef hlutur "
               "hefur eigið gildi er það notað. Þannig má láta einn hlut "
               "víkja frá tegundinni sinni.",
               "**An instance value always wins over the type.** If an "
               "element has its own value, that value is used. That is how "
               "one element can differ from its type.")),
        h3(L("Dæmi: ein hurð, fullkláruð", "Example: one door, complete")),
        code("CCITopnode[Type]           [L]\n"
             "CCIClassCode[Type]         QQC\n"
             "CCIClassification[Type]    QQC:Door\n"
             "CCITypeID[Type]            %QQC001\n"
             "CCIMultiLevelTypeID        §B.AD.QQC001\n"
             "CCISingleLevelID           #QQC014\n"
             "CCISingleLevelLocationAtID +B01.01.101"),
        h3("CCIClassification"),
        p(L("Þetta eigindi les IFC export Revit sem `Kóði:Lýsing`. Ekki "
            "setja klasann ([L]) fremst: Revit les fyrsta [ ] sem heiti "
            "flokkunarkerfisins. Verkfærið skrifar t.d. `AD:Wall "
            "construction`.",
            "Revit's IFC export reads this parameter as `Code:Description`. "
            "Don't put the topnode ([L]) first: Revit reads the first [ ] as "
            "the name of the classification system. The tool writes e.g. "
            "`AD:Wall construction`.")),
    ]
    return b


def lod_text():
    return [
    (200, L("Áætlað", "Approximate"), L("Almennt stig", "General"),
     L("Teiknað sem almennir hlutir. Stærð, staðsetning og eiginleikar eru "
       "áætluð.",
       "Modelled as generic objects. Size, position and properties are "
       "approximate.")),
    (300, L("Ákveðið", "Defined"), L("Grunnstig verkhluta", "Basic design"),
     L("Teiknað sem ákveðnar tegundir. Stærð, staðsetning og eiginleikar "
       "eru ákveðin.",
       "Modelled as specific types. Size, position and properties are "
       "defined.")),
    (325, L("Endanlegt", "Final"), L("Hönnunarstig verkhluta",
                                     "Detailed design"),
     L("Nákvæmar og skilgreindar tegundir. Upplýsingar á endanlegu stigi.",
       "Detailed, specified types. Information is final.")),
    (400, L("Endanlegt og nákvæmt", "Final and precise"),
     L("Framleiðslustig", "Production"),
     L("Teiknað eftir efnislegum vörum og efnisvali, fyrir framleiðslu og "
       "framkvæmd.",
       "Modelled from actual products and materials, for production and "
       "construction.")),
]


def page_lod():
    b = [
        h2(L("Þróunarstig (LOD)", "Level of development (LOD)")),
        p(L("Þróunarstig segir hversu langt hver byggingarhluti er kominn í "
            "líkaninu: hversu áreiðanlegar upplýsingarnar eru (LOR), hversu "
            "nákvæm rúmfræðin er (LOG) og hvaða upplýsingar fylgja (LOI). "
            "Hér er notuð skilgreining DiKon, BIM7AA og Molio, sem BIM "
            "Ísland hefur þýtt: *Þróunarstig byggingarhluta*.",
            "The level of development says how far each element has come in "
            "the model: how reliable the information is (LOR), how detailed "
            "the geometry is (LOG) and which information comes with it "
            "(LOI). This uses the DiKon, BIM7AA and Molio definition, "
            "translated by BIM Ísland: *Þróunarstig byggingarhluta*.")),
        table(["LOD", L("Áreiðanleiki (LOR)", "Reliability (LOR)"),
               L("Rúmfræði (LOG)", "Geometry (LOG)"),
               L("Hvað það þýðir", "What it means")],
              [["%d DK" % n, r, g, d] for n, r, g, d in lod_text()]),
        note(L("LOD er ekki bundið við áfanga verkefnis. Mismunandi "
               "byggingarhlutar geta verið á mismunandi stigi á sama tíma; "
               "þess vegna er LOD stillt fyrir hvern hóp í Uppsetningu "
               "verkefnis.",
               "LOD is not tied to project stages. Different element groups "
               "can be at different levels at the same time; that is why "
               "LOD is set per group in Project setup.")),
        p(L("Stundum er LOD skrifað |200|325|300|: LOR, LOG og LOI hvert "
            "fyrir sig. Þá er það LOR (fyrsta talan) sem ræður "
            "áreiðanleikanum.",
            "LOD is sometimes written |200|325|300|: LOR, LOG and LOI "
            "separately. LOR (the first number) then decides the "
            "reliability.")),
        h3(L("Hvenær þarf CCI kóða?", "When are CCI codes required?")),
        p(L("Samkvæmt Þróunarstigi byggingarhluta (eiginleiki 9.1 Flokkun) "
            "þarf flokkunarkóða og tegundarauðkenni frá LOD 300. Á LOD 200 "
            "eru hlutir enn almennir og verkfærið gerir ekki villu þótt kóða "
            "vanti.",
            "Under Þróunarstig byggingarhluta (property 9.1 Classification), "
            "class code and type ID are required from LOD 300. At LOD 200 "
            "objects are still generic, and the tool doesn't report missing "
            "codes as errors.")),
    ]
    rows = []
    for gid in groups.GROUP_IDS:
        gate = groups.min_lod_for_classification(gid)
        extra = ""
        if gid == "openings":
            extra = L("Einstakt auðkenni (#) við LOD 400",
                      "Unique ID (#) at LOD 400")
        rows.append([t("group." + gid), "LOD %d" % gate, extra])
    b.append(table([L("Byggingarhluti", "Element group"),
                    L("Flokkun og tegundarauðkenni frá", "Class and type "
                      "ID from"), L("Annað", "Other")], rows))
    return b


def page_scope():
    rows = []
    for sc in groups.SCOPES:
        rows.append([t("scope." + sc),
                     ", ".join(formats.PARAM[f] for f in
                               groups.SCOPE_FIELDS[sc])])
    return [
        h2(L("Umfang kóðunar", "Scope of coding")),
        p(L("Það þarf ekki alltaf að fylla út öll CCI eigindi. Í upphafi "
            "verkefnis er umfangið ákveðið út frá því hvað verkkaupi og "
            "rekstraraðili þurfa (CCI leiðbeiningar BIM Íslands, bls. 1). "
            "Verkfærið fyllir aðeins út og athugar það sem er hakað við.",
            "You don't always need every CCI parameter. At the start of a "
            "project the scope is decided from what the client and "
            "operator need (BIM Ísland's CCI guidelines, p. 1). The tool "
            "only fills in and checks what is ticked.")),
        table([L("Umfang", "Scope"), L("Eigindi", "Parameters")], rows),
        h3(L("Hvernig vel ég?", "How do I choose?")),
        ul(L("**Samræmd upplýsingamiðlun**: nær alltaf. Grunnurinn fyrir "
             "magnskrá, útboð og samræmingu.",
             "**Coordinated information exchange**: almost always. The "
             "basis for quantities, tendering and coordination."),
           L("**Rekstur**: ef líkanið á að nýtast í rekstri hússins.",
             "**Operations**: if the model will be used to run the "
             "building."),
           L("**Kerfismyndir**: fyrir lagnir og stjórnbúnað; yfirleitt "
             "verk lagnahönnuða.",
             "**System diagrams**: for MEP and controls; usually the MEP "
             "engineers' job."),
           L("**Vöruauðkenni** og **Staðsetningarauðkenni**: þegar þarf að "
             "þekkja einstaka hluti og hvar þeir eru, t.d. fyrir viðhald.",
             "**Product ID** and **Location ID**: when single items and "
             "their location must be known, e.g. for maintenance.")),
        note(L("Flokkaðu ekki meira en verkefnið þarf. Meiri kóðun er meiri "
               "vinna að halda réttri.",
               "Don't classify more than the project needs. More coding is "
               "more work to keep right.")),
    ]


def faq_explain():
    return {
    "chk.not_bound": (
        L("Hluturinn hefur ekki eigindið sem umfangið krefst.",
          "The element doesn't have a parameter the scope requires."),
        L("Keyrðu Eigindi. Ef það er generic model eða sérstakur flokkur: "
          "athugaðu hvort hann á að fara í IFC.",
          "Run Parameters. For generic models or special categories, check "
          "whether they should be exported to IFC at all.")),
    "chk.missing": (
        L("Eigindið er til en tómt.", "The parameter exists but is empty."),
        L("Keyrðu Flokka (flokkun) eða Númera (auðkenni). Rými: Staðsetning.",
          "Run Classify (class) or Number (IDs). Rooms: Locations.")),
    "chk.not_applicable": (
        L("Gildi er í eigindi sem á ekki við þessa gerð hlutar, t.d. "
          "kerfisauðkenni á hurð.",
          "A value is in a parameter that doesn't apply to this kind of "
          "element, e.g. a function ID on a door."),
        L("Hreinsaðu gildið, eða láttu vera ef það er viljandi.",
          "Clear the value, or leave it if it is deliberate.")),
    "chk.format": (
        L("Gildið er ekki á réttu sniði (sjá flipann Eigindi og gildi).",
          "The value is not in the right format (see the Parameters tab)."),
        L("Leiðréttu handvirkt, eða keyrðu Flokka/Númera aftur.",
          "Correct it by hand, or run Classify/Number again.")),
    "chk.override": (
        L("Hluturinn hefur annað gildi en tegundin hans. Það er leyft, en "
          "oft leifar af eldri kóðun.",
          "The element has a different value from its type. That's allowed, "
          "but often left over from old coding."),
        L("Ef það er ekki viljandi: Flokka > hakaðu við 'Yfirskrifa líka "
          "kóða sem eru settir á einstaka hluti'.",
          "If not deliberate: Classify > tick 'Also overwrite codes set on "
          "single elements'.")),
    "chk.unknown_class": (
        L("Kóðinn er ekki í CCI töflunni sem er í notkun. Oft eldri CCS "
          "kóði eða innsláttarvilla.",
          "The code isn't in the CCI table in use. Often an old CCS code or "
          "a typo."),
        L("Flokka > Skipta út eldri kóðun, eða Velja úr töflu.",
          "Classify > Replace old coding, or Pick from table.")),
    "chk.unverified_class": (
        L("Taflan er merkt ófullgerð, svo ekki er hægt að staðfesta kóðann.",
          "The table is marked incomplete, so the code can't be confirmed."),
        L("Lestu inn fulla töflu í CCI tafla.",
          "Load a full table in CCI table.")),
    "chk.id_class_mismatch": (
        L("Auðkennið (t.d. %QQB001) passar ekki við flokkunina (t.d. QQC). "
          "Gerist þegar flokkun er breytt.",
          "The ID (e.g. %QQB001) doesn't match the class (e.g. QQC). Happens "
          "when a class is changed."),
        L("Keyrðu Númera.", "Run Number.")),
    "chk.classification_mismatch": (
        L("CCIClassification hefur annan kóða en CCIClassCode.",
          "CCIClassification has a different code from CCIClassCode."),
        L("Keyrðu Flokka.", "Run Classify.")),
    "chk.classification_topnode": (
        L("CCIClassification byrjar á [L]; IFC export Revit les það sem "
          "heiti kerfisins.",
          "CCIClassification starts with [L]; Revit's IFC export reads that "
          "as the system name."),
        L("Keyrðu Flokka.", "Run Classify.")),
    "chk.duplicate": (
        L("Sama auðkenni er á fleiri en einum hlut eða rými.",
          "The same ID is on more than one element or room."),
        L("Vöruauðkenni: Númera. Rýmisnúmer: athugaðu Number rýmanna.",
          "Product IDs: Number. Room numbers: check the rooms' Number.")),
    "chk.duplicate_type_id": (
        L("Tvær tegundir hafa sama tegundarauðkenni.",
          "Two types share one type ID."),
        L("Keyrðu Númera; það gefur annarri tegundinni nýtt númer.",
          "Run Number; it gives one of them a new number.")),
}


def page_faq():
    b = [
        h2(L("Algeng vandamál", "Common problems")),
        p(L("Hvað athugasemdirnar í **Athuga** þýða og hvernig á að laga "
            "þær.",
            "What the findings in **Check** mean and how to fix them.")),
    ]
    faq = faq_explain()
    for key in sorted(faq, key=lambda k: t(k + ".h")):
        what, fix = faq[key]
        b.append(h3(t(key + ".h")))
        b.append(ul(L("**Hvað:** ", "**What:** ") + what,
                    L("**Lausn:** ", "**Fix:** ") + fix))
    b += [
        h2(L("Spurningar", "Questions")),
        h3(L("Af hverju % fyrir framan tegundarauðkennið?",
             "Why % in front of the type ID?")),
        p(L("Forskeytin segja hvers konar auðkenni þetta er: % tegund, # "
            "eintak, § samsett tegund, = kerfi, + staðsetning. Þau koma úr "
            "CCI leiðbeiningum BIM Íslands.",
            "The prefixes say what kind of ID it is: % type, # single item, "
            "§ multi-level type, = system, + location. They come from BIM "
            "Ísland's CCI guidelines.")),
        h3(L("Líkanið hefur eldri kóðun. Hvað geri ég?",
             "The model has old coding. What do I do?")),
        p(L("Flokka > hakaðu við 'Aðeins eldri/önnur kóðun' til að sjá hana, "
            "svo 'Skipta út eldri kóðun'. Ekkert er skrifað fyrr en þú "
            "smellir á Skrifa í líkan. Númera endurskrifar svo auðkennin.",
            "Classify > tick 'Old/other coding only' to see it, then "
            "'Replace old coding'. Nothing is written until you click Write "
            "to model. Number then rewrites the IDs.")),
        h3(L("Við höfum ekki shared parameter skrá Molio.",
             "We don't have Molio's shared parameter file.")),
        p(L("Ef líkanið hefur eigindin þegar: Eigindi > Vista skrá úr þessu "
            "verkefni. Annars: skrá verkfærisins. IFC skil eru eins með "
            "báðum, og hægt er að skipta yfir í skrá Molio síðar án þess að "
            "gildi tapist.",
            "If the model already has the parameters: Parameters > Save the "
            "file from this project. Otherwise: the tool's own file. IFC "
            "deliveries are the same with either, and you can switch to "
            "Molio's file later without losing values.")),
        h3(L("Er tillaga verkfærisins alltaf rétt?",
             "Is the tool's suggestion always right?")),
        p(L("Nei. 'Leiðbeiningar' þýðir að kóðinn er dæmi í leiðbeiningum "
            "BIM Íslands eða Molio. 'Tillaga' er mat verkfærisins út frá "
            "flokki og heiti. Farðu alltaf yfir Yfirlit flokkunar í Athuga.",
            "No. 'Guidelines' means the code is an example in BIM Ísland's "
            "or Molio's guides. 'Suggestion' is the tool's guess from the "
            "category and name. Always review the Classification overview "
            "in Check.")),
    ]
    return b


def glossary():
    return [
    ("Flokkun", "Classification", "Klassifikation",
     L("Hvers konar hlutur þetta er, t.d. hurð.",
       "What kind of thing it is, e.g. a door.")),
    ("Auðkenni", "Identification", "Identifikation",
     L("Hvaða hlutur nákvæmlega, t.d. hurð nr. 14.",
       "Exactly which thing, e.g. door no. 14.")),
    ("Klasi", "Topnode / domain", "Topnode / domæne",
     L("Hvaða tafla kóðinn er úr: [L] byggingarhlutar, [B] rými...",
       "Which table the code is from: [L] elements, [B] spaces...")),
    ("Virknikerfi", "Functional system", "Funktionelt system",
     L("Efsta stig, 1 stafur, t.d. B veggir.",
       "Top level, 1 letter, e.g. B walls.")),
    ("Tæknikerfi", "Technical system", "Teknisk system",
     L("2 stafir, t.d. AD vegguppbygging.",
       "2 letters, e.g. AD wall construction.")),
    ("Byggingarhluti", "Component", "Komponent",
     L("3 stafir, t.d. QQC hurð.", "3 letters, e.g. QQC door.")),
    ("Tegundarauðkenni", "Type ID", "Type-ID",
     L("%QQC001: tegund 1 af hurðum.", "%QQC001: door type 1.")),
    ("Vöruauðkenni", "Product ID", "Produkt-ID",
     L("#QQC014: eitt ákveðið eintak.", "#QQC014: one specific item.")),
    ("Kerfisauðkenni", "Function ID", "Funktions-ID",
     L("=H01.HD02.EGC001: staður í lagnakerfi.",
       "=H01.HD02.EGC001: place in a system.")),
    ("Rýmisnúmer", "Room number", "Rumnummer",
     L("B01.01.001: bygging, hæð, rými.", "B01.01.001: building, storey, "
       "room.")),
    ("Þróunarstig", "Level of development (LOD)", "Udviklingsniveau",
     L("Hversu langt byggingarhluti er kominn.",
       "How far an element has come.")),
    ("Eigindi", "Parameter / property", "Egenskab",
     L("Reitur í Revit sem geymir gildi.", "A Revit field that holds a "
       "value.")),
    ("Umfang", "Scope", "Omfang",
     L("Hvaða CCI upplýsingar verkefnið krefst.",
       "Which CCI information the project requires.")),
    ("Eigindasafn", "Property set (Pset)", "Egenskabssæt",
     L("Hópur eiginda í IFC, t.d. CCI_Administrative.",
       "A group of properties in IFC, e.g. CCI_Administrative.")),
]


def page_glossary():
    return [
        h2(L("Orðasafn", "Glossary")),
        p(L("Íslensk, ensk og dönsk heiti, svo auðvelt sé að lesa "
            "leiðbeiningar Molio og BIM Íslands saman.",
            "Icelandic, English and Danish terms, so Molio's and BIM "
            "Ísland's guides are easy to read together.")),
        table([L("Íslenska", "Icelandic"), L("Enska", "English"),
               L("Danska", "Danish"), L("Merking", "Meaning")],
              [list(g) for g in glossary()]),
        h3(L("Heimildir", "Sources")),
        ul("BIM Ísland, *CCI leiðbeiningar*, " + L("útgáfa", "edition") +
           " 2 (2023). bim.is",
           "BIM Ísland, *CCI leiðbeiningar fyrir Revit* (2023). bim.is",
           "DiKon / BIM7AA / Molio, *Þróunarstig byggingarhluta* REV4 "
           "(BIM Ísland, 2022).",
           "Molio, *CCS Introduktion og overblik for arkitekter* (2020).",
           "Molio, CCI " + L("flokkunartöflur", "classification tables") +
           " P150 (R1, 2020). ikt.molio.dk"),
    ]


def pages(lang, class_table=None):
    """[{"id", "title", "blocks"}]; the 'browser' page is interactive
    and has no blocks."""
    LANG[0] = lang
    return [
        {"id": "steps", "title": L("Skref fyrir skref", "Step by step"),
         "blocks": page_steps()},
        {"id": "cci", "title": L("Hvað er CCI?", "What is CCI?"),
         "blocks": page_cci(class_table)},
        {"id": "params", "title": L("Eigindi og gildi", "Parameters"),
         "blocks": page_params()},
        {"id": "lod", "title": L("Þróunarstig", "LOD"),
         "blocks": page_lod()},
        {"id": "scope", "title": L("Umfang", "Scope"),
         "blocks": page_scope()},
        {"id": "faq", "title": L("Algeng vandamál", "Common problems"),
         "blocks": page_faq()},
        {"id": "browser", "title": L("CCI vafri", "CCI browser"),
         "blocks": []},
        {"id": "glossary", "title": L("Orðasafn", "Glossary"),
         "blocks": page_glossary()},
    ]


def model_status(info):
    """Rows for the 'Model status' check in the steps page.

    info: {"setup": bool, "params": (bound, total), "types": (classified,
    total), "type_ids": (with, total), "rooms": (with, total)}.
    Returns [(step name, done: True/False/None, detail)].
    """
    rows = []
    rows.append((btn("setup"), info.get("setup"),
                 L("Stillingar vistaðar", "Settings saved")
                 if info.get("setup") else
                 L("Ekki keyrt", "Not run yet")))
    b, n = info.get("params", (0, 0))
    rows.append((btn("params"), b == n and n > 0,
                 L("%d af %d eigindum", "%d of %d parameters") % (b, n)))
    for key, name in (("types", "classify"), ("type_ids", "number"),
                      ("rooms", "locations")):
        done, total = info.get(key, (0, 0))
        state = None if not total else done == total
        rows.append((btn(name), state,
                     L("%d af %d", "%d of %d") % (done, total)))
    return rows


# ------------------------------------------------------------ rendering

_INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def inline(text):
    """'a **b** `c`' -> [('', 'a '), ('b', 'b'), ('', ' '), ('c', 'c')].

    Kinds: '' plain, 'b' bold, 'i' italic, 'c' code.
    """
    out = []
    for part in _INLINE.split(text or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(("b", part[2:-2]))
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(("c", part[1:-1]))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(("i", part[1:-1]))
        else:
            out.append(("", part))
    return out


BROWSER_DOMAINS = [("L", "[L]"), ("S", "[A]"), ("E", "[E]"), ("D", "[D]")]


def domain_label(domain):
    return {"L": L("Byggingarhlutar [L]", "Building elements [L]"),
            "S": L("Rými [A] / [B]", "Spaces [A] / [B]"),
            "E": L("Mannvirki [E]", "Construction entities [E]"),
            "D": L("Hjálpargögn [D]", "Construction aids [D]")}[domain]


def level_label(entry, code):
    kind = entry.get("table", "")
    if kind == "functional":
        return L("Virknikerfi", "Functional system")
    if kind == "technical":
        return L("Tæknikerfi", "Technical system")
    if kind == "component":
        return L("Byggingarhluti", "Component")
    return L("Stig %d", "Level %d") % (entry.get("level") or len(code))


def browser_detail(ct, domain, code, lang):
    """[(label, value)] for the detail pane of the CCI browser."""
    LANG[0] = lang
    top = dict(BROWSER_DOMAINS)[domain]
    e = ct.domains.get(domain, {}).get(code)
    if not e:
        return []
    rows = [(L("Kóði", "Code"), code),
            (L("Stig", "Level"), level_label(e, code)),
            (L("Leið", "Path"), ct.path(code, lang, top))]
    if lang == "is":
        n = ct.name(code, "is", top)
        rows.append((L("Íslenska", "Icelandic"),
                     n if not n.startswith("(") else
                     L("(ekki þýtt enn)", "(not translated yet)")))
    rows.append((L("Enska", "English"), e.get("en", "")))
    rows.append((L("Danska", "Danish"), e.get("da", "")))
    if e.get("def_en"):
        rows.append((L("Skilgreining", "Definition"), e["def_en"]))
    if e.get("def_da"):
        rows.append((L("Skilgreining (DA)", "Definition (DA)"),
                     e["def_da"]))
    if domain == "L":
        rows.append((L("Í Revit", "In Revit"),
                     "CCIClassCode[Type] = %s · CCITopnode[Type] = [L] · "
                     "CCIClassification[Type] = %s" % (
                         code, formats.classification(code, e.get("en")))))
        if len(code) == 3:
            rows.append((L("Tegundarauðkenni", "Type ID"), "%" + code +
                         "001"))
    elif domain == "S":
        rows.append((L("Í Revit", "In Revit"),
                     "CCIClassCode = %s · CCITopnode = [A] / [B]" % code))
    return rows
