# CCI-IS (pyRevit viðbót)

CCI flokkun í Revit samkvæmt leiðbeiningum BIM Íslands:
*CCI leiðbeiningar* (útgáfa 2, 11.01.2023), *CCI leiðbeiningar fyrir Revit*
(útgáfa 1, 30.01.2023) og *Þróunarstig byggingarhluta* (REV4). Sama
verkfæri er til á ensku sem **CCI-EN**; settu aðeins annað þeirra upp.

## Uppsetning
Settu möppuna `CCI-IS.extension` í `%APPDATA%\pyRevit\Extensions\` og
smelltu á Reload í pyRevit. Flipinn **CCI** birtist. Revit 2024 eða nýrra,
IronPython vél pyRevit.

## Röð verka
1. **Uppsetning verkefnis**: hakaðu við umfang (BIM Ísland, bls. 1), settu
   númer byggingar, hæðakóða (01, K1, M2) og þróunarstig hvers
   byggingarhluta. Vistast í verkefninu, svo allir á miðlægu líkani deila
   sömu stillingum.
2. **CCI tafla**: sýnir hvaða CCI tafla er í notkun og les inn nýrri
   (sjá að neðan). Fylgir með töflum Molio frá 2020-05-26 (R1).
3. **Eigindi**: setur eigindin 11 (auk `CCIClassification`) undir
   Identity Data, `[Type]` sem type eigindi og hin sem instance, aðeins á
   þá flokka sem þau eiga við. Veldu skrá Molio eða skrá verkfærisins
   (sjá *Shared parameter skrá*).
4. **Flokka**: ein lína fyrir hverja tegund (og hvert rýmisheiti) með
   tillögu að flokkun. Breyttu, taktu hak af því sem á að bíða og smelltu á
   *Skrifa í líkan*. Skrifar `CCIClassCode[Type]`, `CCITopnode[Type]` og
   `CCIClassification[Type]`. Ef hlutir eru valdir birtast aðeins tegundir
   þeirra. *Velja úr töflu* leitar í allri CCI töflunni. Dálkurinn
   *Heimild* segir hvaðan tillagan kemur (Leiðbeiningar = BIM Ísland/Molio,
   Tillaga = verkfærið, Stofan = regla stofunnar). Hakaðu við *Muna* og
   flokkunin er vistuð sem regla stofunnar fyrir þá fjölskyldu og tegund
   (eða rýmisheiti).
5. **Númera**: `%QQC001`, `§B.AD.QQC001` og `#QQC001`, eftir umfangi.
6. **Staðsetning**: `B01.01.001` á rými, `+B01.01.001` á hluti í rýmum.
7. **Athuga**: skýrsla með tenglum á hlutina, CSV ef óskað er.
8. **IFC skrá**: býr til `CCI_in_Revit_to_IFC.txt` og sýnir gildin fyrir
   Classification Settings.

## Það sem breytist ekki
- **Númer breytast aldrei.** Tegund eða hlutur heldur sínu númeri. Númer
  eyddra hluta eru ekki endurnýtt. Ef tegund skiptir um flokkun fær hún
  nýtt númer í nýju flokkuninni og gamla númerið er lagt niður. Númer sem
  eru þegar í líkaninu (handslegin) eru tekin upp ef þau eru laus.
- **Instance gildi taka forgang yfir type gildi** (BIM Ísland). Verkfærið
  afritar gildi tegundar á instance eigindi (hægt að slökkva á í
  uppsetningu) en skrifar aldrei yfir gildi sem einhver breytti viljandi.

## Kröfur eftir umfangi og þróunarstigi

| Umfang | Fyllir út / athugar |
|---|---|
| Samræmd upplýsingamiðlun | CCIClassCode, CCITypeID |
| Kerfismyndir og stjórnbúnaður | CCIClassCode, CCIFunctionalID (athugar aðeins snið) |
| Rekstur | CCITopnode, CCIClassCode, CCIMultiLevelTypeID, CCIMultiLevelLocationID |
| Vöruauðkenni | CCISingleLevelID |
| Staðsetningarauðkenni | CCISingleLevelLocationAtID |

Flokkunarkóði og tegundarauðkenni eru aðeins krafa frá **LOD 300** (úrtök
og opnanir frá LOD 325, og einstakt auðkenni við LOD 400), samkvæmt
*Þróunarstigi byggingarhluta*.

## CCI taflan og uppfærslur
Verkfærinu fylgja CCI töflur Molio frá **2020-05-26, R1**
(byggingarhlutar, rýmisnotkun, notkun mannvirkja, byggingarbúnaður:
722 + 148 + 174 + 74 flokkar). Núverandi ókeypis skrár á Molio IKT
(P150a–d) eru sama útgáfa, svo taflan er í gildi í nóvember 2026.
Hnappurinn **CCI tafla**:

- **Uppfæra úr tengli**: límdu inn vefslóð eða slóð á sameiginlegu drifi,
  fleiri en eina með bili á milli. Tekur við töflum Molio (.xlsx, á dönsku
  og/eða ensku) eða töflu á sniði verkfærisins (.json). Tengillinn er
  geymdur svo næsta uppfærsla er einn smellur.
- **Uppfæra úr skrám**: það sama, úr skrám sem þú velur.
- Áður en nokkru er breytt sérðu hvað er nýtt, horfið og með breytt heiti,
  og **hvaða kóðar í opna líkaninu eru ekki í nýju töflunni**. Eldri
  útgáfur eru geymdar; **Skipta um útgáfu** fer til baka.
- **Gagnamappa stofunnar**: sjálfgefið `%APPDATA%\CCI-tools`. Settu hana á
  sameiginlegt drif og öll stofan notar sömu töflu, reglur og íslensk heiti.
  Uppfærsla á viðbótinni snertir hana ekki.

Verkefnið man með hvaða töflu það var flokkað og Athuga segir til ef önnur
tafla er nú í notkun.

JSON töflu má búa til utan Revit: `python tools/build_table.py <xlsx…>`.

## Líkön með eldri kóðun
Mörg líkön hafa þegar CCI (eða CCS) kóðun úr eldra verkfæri eða
sniðmáti. Dálkurinn *Núna* í Flokka sýnir hana.

- **Skipta út eldri kóðun** setur tillögu verkfærisins í stað kóða sem
  víkja frá henni eða eru ekki í CCI töflunni. Virkar á valdar línur, eða
  á allar línur með eldri kóðun ef ekkert er valið. Ekkert er skrifað fyrr
  en smellt er á *Skrifa í líkan*. Línur með eldri kóðun en enga tillögu
  bíða þess að þú veljir kóða úr töflunni.
- **Yfirskrifa líka kóða sem eru settir á einstaka hluti**: venjulega lætur
  verkfærið instance gildi í friði, því BIM Ísland leyfir þeim að víkja
  viljandi frá tegundinni. Hakaðu við þetta til að hreinsa eldri kóða af
  einstökum hlutum líka.
- **Númera** endurskrifar tegundarauðkenni og vöruauðkenni eftir núverandi
  flokkun, svo eldri auðkenni eru líka leyst af hólmi. Handgerðar
  undirtegundir (`%QQC01.001`) haldast.
- Verkfærið snertir aðeins tegundir sem eru notaðar í líkaninu. Ónotaðar
  tegundir halda því sem þær höfðu.
- Ef sniðmátið hefur `CCIClassName[Type]` og `CCIClassCodeVersion[Type]`,
  eins og skrá Molio, fyllir Flokka þau líka út: enska heiti flokksins og
  útgáfu töflunnar (R1).

## CCIClassification og IFC
IFC export Revit les flokkunarreitinn sem `[Kerfi]Kóði:Lýsing`.
Verkfærið skrifar `AD:Wall construction`: kóðann og enska heitið frá
Molio. Heiti kerfisins kemur úr IFC Classification Settings („CCI
Classification“) og klasinn hefur eigið eigindi, eins og IDS BIM Íslands
gerir ráð fyrir. Eldri útgáfur verkfærisins skrifuðu `[L]AD`, sem Revit
myndi flytja út sem flokkunarkerfi sem heitir „L“. Athuga merkir það snið
og það lagast ef Flokka er keyrt aftur. Gildi eins og
`[CCI][L]AD:Wall construction` úr öðrum verkfærum eru tekin gild.

Property set skráin varpar CCI eigindunum sem `Text`, eins og í
leiðbeiningum BIM Íslands. Þetta eru kóðar en ekki tölur, svo texti er
réttur.

## Athuga
Auk villna sýnir Athuga **yfirlit flokkunar**: hvern flokk (category) og
kóðana sem hann fékk, með heitum og fjölda. Þar sérðu ef eitthvað er
rangt flokkað. Sjálf athugunin sannreynir snið og að kóðinn sé til í
töflunni, ekki hvort hann sé rétti kóðinn fyrir hlutinn. Hlutum sem eiga
ekki að fara í IFC er sleppt. Hlutir utan þróunarstigshópanna (generic
models o.fl.) gefa aðeins viðvaranir.

Athuga listar líka **eldri CCI/CCS eigindi** í verkefninu sem eru ekki á
lista BIM Íslands og verkfærið notar ekki, t.d. `CCITypeID_Type`,
`CCITypeName_Type` eða gömul `CCS*` eigindi. Fyrir hvert eigindi sést hvort
það er type eða instance, hversu margir hlutir hafa gildi og í hvaða
skrám (schedules) það er notað. Ónotuð eigindi má yfirleitt fjarlægja í
Manage > Project Parameters.

## Shared parameter skrá
Opinbera CCI shared parameter skrá Molio og IFC property set skráin eru
verkfærapakkinn **C420 + C421** í áskriftinni *CAD og bygningsmodel* hjá
Molio, sem er greidd. Ókeypis aðgangur að Molio IKT gefur CCI töflurnar
(P150) en ekki þessar skrár.

Þangað til stofan hefur C420 setur **Eigindi > Skrá verkfærisins** inn
sömu eigindanöfn úr skrá sem verkfærið skrifar sjálft. Það þýðir:

- **IFC skil eru eins.** IFC export varpar eigindunum eftir nafni
  (`CCI_in_Revit_to_IFC.txt`, sem IFC hnappurinn skrifar eftir
  leiðbeiningum BIM Íslands), og IDS athuganir BIM Íslands lesa IFC
  skrána. Hvorugt sér GUID.
- **GUID eru önnur en hjá Molio.** Revit þekkir shared parameters á GUID,
  svo líkan sem notar skrá Molio og líkan sem notar skrá verkfærisins
  deila ekki skrám (schedules) eða merkjum (tags) milli tenginga, og
  afrita/líma milli þeirra getur búið til annað `CCIClassCode`. GUID
  verkfærisins eru þau sömu í öllum eintökum þess, svo samstarfsaðilar
  geta notað sömu skrá: **Eigindi > Vista skrá verkfærisins**.
- **Örugg skipti síðar.** Þegar C420 fæst skaltu keyra **Eigindi > Skrá
  Molio**. Verkfærið býðst til að færa verkefnið yfir: les öll gildi,
  skiptir um eigindi og skrifar gildin aftur, allt í einu skrefi sem má
  afturkalla. Athuga segir hvaða skrá verkefnið notar. Fjölskyldur
  (families) sem hafa CCI eigindin innbyggð þarf að uppfæra sérstaklega.
- **Ef líkan hefur þegar CCI eigindin** (t.d. úr sniðmáti stofunnar)
  vistar **Eigindi > Vista skrá úr þessu verkefni** shared parameter skrá
  með GUID þess verkefnis. Notaðu hana fyrir önnur verkefni og þá passa
  öll verkefni við sniðmátið.
- Ef skrá Molio stafar nafn öðruvísi í há-/lágstöfum (IDS skýrsla BIM
  Íslands skrifar `CCITopNode`, Revit leiðbeiningarnar `CCITopnode`)
  notar verkfærið þá stafsetningu sem er í verkefninu.

## Íslensk heiti
419 af 1.044 flokkum hafa íslensk heiti (auk 67 hópheita): öll
virknikerfi og tæknikerfi, öll
rýmisnotkun, flokkahópar byggingarhluta, algengustu byggingarhlutar
arkitekta og hópar mannvirkja. Heiti sem BIM Ísland notar eru merkt
`bim_island`; **hin eru drög og þarf að yfirfara** af einhverjum sem
þekkir íslensk byggingarhugtök. Flokkar án heitis eru sýndir á ensku í
sviga.

Yfirlestur: **CCI tafla > Flytja út íslensk heiti (CSV)**, lagaðu dálkinn
`is` í Excel, settu `reviewed` í `status` og veldu svo **Lesa inn
íslensk heiti**. Heitin vistast í gagnamöppunni. Ef ný tafla breytir
ensku heiti er íslenska heitið merkt `stale` í útflutningnum svo hægt sé
að athuga það.

## Reglur
Hvaða flokkun Revit tegund fær ræðst af reglum: reglum stofunnar
(í gagnamöppunni, prófaðar fyrst) og sjálfgefnum reglum
(`data/rules.json`, búnar til með `tools/make_rules.py`). Regla getur
skoðað flokk (category), heiti fjölskyldu/tegundar, rýmisheiti, type
eigindi, burðarvirki og kerfisveggi. Reglur með `match` eru prófaðar á
undan almennum reglum. Sjálfgefnu reglurnar ná yfir helstu flokka
arkitekta, grunnatriði lagna og rafkerfa, og rýmisheiti á íslensku, ensku
og dönsku (Stofa → AAB, Stigagangur → EAD, Sorpgeymsla → CAA…).

## Þar sem skjölunum ber ekki saman, og hvað verkfærið gerir
- Tegundarauðkenni `%AD001` (CCI leiðbeiningar v2) eða `%AD1` (Þróunarstig,
  eiginleikatafla): verkfærið fylgir v2 og fjöldi tölustafa er stilling.
- Eigindasafn `CCI_Administrative` (Revit leiðbeiningar) eða
  `CCS_Administrative` (Þróunarstig): verkfærið notar `CCI_Administrative`.
- `CCIClassification` er ekki meðal eigindanna 11, en „Classification
  field name“ í IFC export vísar á það. Verkfærið fyllir það út (`[L]AD`)
  ef eigindið er til. **Prófaðu** í IFC export Revit að `[L]` sé ekki lesið
  sem heiti flokkunarkerfisins; ef svo er, taktu hakið af „með klasa á
  undan“ í uppsetningu.
- **Reykloka**: dæmi BIM Íslands nota `QMB` fyrir reykloku, en í töflu
  Molio er `QMB` „On-off spjæld / Gas shutoff valve“ og reykloka er `FMB`
  (Røgspjæld). Verkfærið setur reykloku á `FMB` og lokunarspjöld á `QMB`.
  Rétt væri að staðfesta þetta við BIM Ísland.
- Leiðbeiningar Molio fyrir arkitekta (CCS, 2020) nota suma eldri CCS kóða
  (t.d. `XLD` salerni); verkfærið notar kóða CCI töflunnar (`XKB`).
- Töflum Molio ber sjálfum ekki saman á nokkrum stöðum (t.d. rými `AAA` er
  „Room“ í ensku skránni en „Courtyard“ í enska dálki dönsku skrárinnar;
  byggingarhluti `RLC` kemur tvisvar fyrir). Innlesturinn tekur hvert
  tungumál úr eigin skrá og sýnir allt misræmi.
- Eistneska/alþjóðlega CCI-EE sniðmátið er önnur útgáfa CCI (CCIC, ekki
  Molio) og er ekki notað.
- Dæmið `B2.K2.010` (yfirlitstafla) eða `Bxx` (nánari lýsing): verkfærið
  notar tvo tölustafi, `B02.K2.010`.
- `§U.VV.XXXbbb`: „bbb“ er lýst sem númeri fyrir hvert stak, en dæmin sýna
  tegundarnúmer. Sjálfgefið: tegundarnúmer; hægt að breyta í uppsetningu.

## Ekki komið
- Prófun á flutningi eiginda við raunverulega C420 skrá Molio.
- Yfirlestur íslensku heitanna.
- Sjálfvirk `CCIFunctionalID` (kerfisnúmerun er verk lagnahönnuða;
  verkfærið athugar sniðið).
- Hlutum í tengdum líkönum (linked models) er ekki breytt.

Leiðbeiningar: BIM Ísland (bim.is). CCI flokkar: Molio. Athugaðu
leyfisskilmála taflna Molio áður en þýddri töflu er dreift út fyrir stofuna.
