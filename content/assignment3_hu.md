# 3. beadandó — Együttműködés függvényekkel és relációkkal

## Áttekintés
Háromfős csapatokban dolgozzatok! Feladatotok egy rövid porozitási furatdiagram elemzése a függvény- és relációelmélet pontos nyelvén. Szorosan működjetek együtt: minden kérdés feltételezi, hogy a csoport közösen egyeztette a halmazokat, jelöléseket és szimbólumokat.

## Együttműködési szabályok
- Tartsatok három közös megbeszélést (indítás, félidős egyeztetés, záró ellenőrzés). A jegyzetelést rotáljátok.
- Közös dokumentumban vagy táblázatban dolgozzatok, amelyben minden válasz szerkeszthető. Kövessétek, ki vezette és ki lektorálta az egyes kérdéseket.
- Egyetlen összevont jelentést adjatok le, amelyhez mellékelitek a mindhárom tag által aláírt együttműködési naplót.

## Javasolt szereposztás
- **A hallgató – Tartomány- és adatfelelős:** Q1–Q3 vezetése, a jelölésjegyzék karbantartása, a mértékegységek egységesítése.
- **B hallgató – Adattisztaság és alternatív relációk:** Q4–Q6 vezetése, a duplikált/zajos mérések kezelési szabályának dokumentálása és mélység–mélység relációk definiálása.
- **C hallgató – Logikai és kommunikációs felelős:** Q7–Q9 vezetése, szimbolikus állítások hétköznapi nyelvre fordítása, valamint a végső beszámoló sablonjának elkészítése.
- **Teljes csapat:** A Q10 közös kidolgozása és az egész beadandó végső ellenőrzése.

## Mérföldkövek
1. **Indító megbeszélés (1. nap, 30 perc):** Dataset kiválasztása, jelölésjegyzék összeírása, kérdésfelelősök kiosztása.
2. **Önálló szakasz (2–3. nap):** A felelősök első változatokat készítenek, megjelölve a lektorálást igénylő részeket.
3. **Félidős egyeztetés (3. nap, 45 perc):** Feltételezések ellenőrzése (pl. céltartomány megválasztása), jelölések összehangolása.
4. **Keresztlektorálás (4. nap):** Minden hallgató legalább három olyan választ ellenőriz, amelyet nem ő írt.
5. **Záró egyeztetés és beadás (5. nap, 45 perc):** Q10 véglegesítése, nyelvi csiszolás, együttműködési napló összeállítása.

## Leadandók
1. **Fő jelentés** (PDF vagy DOCX), amely tartalmazza:
   - A Q1–Q10 kidolgozott válaszait egységes jelöléssel.
   - A táblázatokat vagy ábrákat (ha vannak) mértékegységek feltüntetésével (m, porozitás arány).
2. **Együttműködési napló** (legfeljebb 1 oldal), amely kérdésenként felsorolja: vezető szerző, lektor, végső jóváhagyó, megbeszélés dátumai.
3. **Opcionális:** Egyszerű folyamatábra arról, hogyan dönti el a csapat, hogy egy reláció függvénynek tekinthető-e.

---

## Kérdések (válaszoljatok teljes mondatokban, általában 2–4 mondatban)
1. **Értelmezési tartomány és céltartomány:** Adjátok meg az \(A\) halmazt (mélységek, méterben) és a \(B\) halmazt (porozitásértékek). Indokoljátok, miért biztosítják ezek a precíz következtetést.
2. **Rendezett párok felírása:** Alakítsátok át az adatokat \(M\) rendezett párok halmazává \((z, \varphi)\). Írjátok le, mit jelent fizikailag minden egyes pár.
3. **Függvényteszt:** Vizsgáljátok meg, hogy a görbe függvényt ad-e \(A\)-ból \(B\)-be. Hivatkozzatok az „egy bemenet → egy kimenet” szabályra, és támasztjátok alá a döntést adatpéldákkal.
4. **Duplikátum-kezelési szabály:** Ha ugyanazon mélységnél több porozitásértéket mér a műszer, rögzítsétek a csapat szabályát a feloldásra, és mutassatok be egy konkrét példát.
5. **Értékkészlet elemzés:** Számítsátok ki a tényleges értékkészletet (kép) a mért porozitásokból. Hasonlítsátok össze a céltartománnyal, és magyarázzátok meg az eltéréseket.
6. **Alternatív reláció meghatározása:** Definiáljatok egy új relációt csak a mélységekre — pl. \(R_{\text{sekély}} = \{(x,y) \in A \times A : x < y\}\). Soroljátok fel a párokat a dataset alapján, és nevezzetek meg egy gyakorlati felhasználást.
7. **Halmaztagsági állítások:** Fordítsatok le három tagsági vagy nem-tagsági állítást (pl. \(1198 \in A\), \(0{,}35 \notin B\), \((1200,0{,}24) \in M\)) hétköznapi nyelvre, kiemelve egy tipikus hibát, amit kerülni kell.
8. **Descartes-szorzat bemutatása:** Mutassátok be \(A \times B\) egy részletét, és magyarázzátok el, miért kell minden relációnak a teljes szorzathalmaz részhalmazának lennie.
9. **Kvantor-gyakorlat:** Írjatok egy egzisztenciális és egy univerzális állítást porozitási küszöbértékekről (pl. \(\exists z \in A: \varphi(z) \ge 0{,}25\)). Döntsétek el, igaz-e az állítás az adatok alapján, és indokoljátok.
10. **Egyedi reláció javaslata (közös munka):** Definiáljatok egy új \(x R y\) relációt, amely kapcsolódik a datasethez (például „x mélységnél legalább akkora a porozitás, mint y-nál”). Bizonyítsátok be, hogy \(R \subseteq A \times A\) vagy \(R \subseteq A \times B\), soroljatok fel legalább három rendezett párt, és írjátok le, hogyan segíthet a reláció a geotudományi döntéshozatalban.

## Értékelési szempontok (összesen 100 pont)
- Fogalmi pontosság és jelölések helyessége (40 pont)
- Együttműködés bizonyítékai (jegyzőkönyvek, keresztlektorálás, közös szószedet) (20 pont)
- Magyarázatok érthetősége, szükség esetén kétnyelvű szószedet használata (20 pont)
- A Q10 közös szintézisének teljessége és koherenciája (20 pont)

Sok sikert! Ne feledjétek: a pontos definíciók teszik védhetővé a geológiai értelmezést.
