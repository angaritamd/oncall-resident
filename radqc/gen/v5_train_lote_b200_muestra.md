# Bloque 200 train v5 — muestra de revisión (10 casos al azar, semilla 44, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B2-0060 · omision (error) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: RX de abdomen para control de litiasis renal conocida en mujer de 42 años.
Correcto — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior con adecuada técnica. Se observan imágenes radiopacas de 4 mm y 6 mm proyectadas sobre la silueta renal derecha, en relación con litiasis conocida. Se identifica lesión lítica expansiva de 35 mm en rama iliopúbica derecha con disrupción cortical, sugestiva de lesión ósea agresiva. No se evidencian niveles hidroaéreos, aire libre subdiafragmático ni otras alteraciones significativas.
Correcto — IMPRESIÓN: Nefrolitiasis derecha estable. Lesión lítica agresiva de 35 mm en rama iliopúbica derecha que requiere correlación con TAC y valoración prioritaria por ortopedia oncológica.
Variante — INDICACIÓN: RX de abdomen para control de litiasis renal conocida en mujer de 42 años.
Variante — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior con adecuada técnica. Se observan imágenes radiopacas de 4 mm y 6 mm proyectadas sobre la silueta renal derecha, en relación con litiasis conocida. Se identifica lesión lítica expansiva de 35 mm en rama iliopúbica derecha con disrupción cortical, sugestiva de lesión ósea agresiva. No se evidencian niveles hidroaéreos, aire libre subdiafragmático ni otras alteraciones significativas.
Variante — IMPRESIÓN: Nefrolitiasis derecha sin cambios significativos respecto a control previo. No otras alteraciones de relevancia.
Esperado [omitted_finding/error]: body='Se identifica lesión lítica expansiva de 35 mm en rama iliopúbica derecha con disrupción cortical, sugestiva de lesión ósea agresiva.' impresion='' (HALLAZGOS describe lesión lítica agresiva de 35 mm que requiere estudio adicional y la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B2-0075 · doble_chequeo (verify) — Angio-TC de tórax

Motivo: Sospecha de tromboembolismo pulmonar con inestabilidad hemodinámica.

Correcto — INDICACIÓN: Angio-TC de tórax por sospecha de tromboembolismo pulmonar con inestabilidad hemodinámica.
Correcto — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias con opacificación homogénea del contraste sin defectos de llenado endoluminales. Aorta torácica de calibre y contornos conservados sin flap de disección. Parénquima pulmonar sin consolidaciones ni áreas de atenuación en vidrio esmerilado. No se evidencia derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Angio-TC de tórax sin signos de tromboembolismo pulmonar. No hay signos de disección aórtica ni otros hallazgos agudos.
Variante — INDICACIÓN: Angio-TC de tórax por sospecha de tromboembolismo pulmonar con inestabilidad hemodinámica.
Variante — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado. Aorta torácica de calibre y contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame pleural.
Variante — IMPRESIÓN: Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.
Esperado [doble_chequeo/verify]: body='sospecha de tromboembolismo pulmonar con inestabilidad hemodinámica' impresion='Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.' (Caso de doble chequeo con indicación crítica informado con plantilla normal que requiere verificación humana y no constituye error.)

- [ ] ✅ / ❌ — comentario:

## B2-0079 · doble_chequeo (verify) — RX de tórax

Motivo: Dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.

Correcto — INDICACIÓN: Hombre de 59 años con dolor torácico súbito tras procedimiento para descartar neumotórax a tensión.
Correcto — HALLAZGOS: Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame pleural. No se observa neumotórax ni signos de tensión mediastínica. Silueta cardiomediastínica de tamaño y contorno normales. Estructuras óseas del tórax sin lesiones agudas.
Correcto — IMPRESIÓN: Sin neumotórax ni criterios de neumotórax a tensión. Radiografía de tórax sin otras alteraciones agudas.
Variante — INDICACIÓN: Hombre de 59 años con dolor torácico súbito tras procedimiento para descartar neumotórax a tensión.
Variante — HALLAZGOS: Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame pleural. Silueta cardiomediastínica de tamaño y contorno normales. Sin neumotórax. Estructuras óseas del tórax sin lesiones agudas.
Variante — IMPRESIÓN: Radiografía de tórax sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar neumotórax a tensión' impresion='Radiografía de tórax sin alteraciones agudas.' (Caso de doble chequeo con indicación crítica informado con plantilla normal; requiere verificación humana y no constituye error.)

- [ ] ✅ / ❌ — comentario:

## B2-0099 · doble_chequeo (verify) — Angio-TC de tórax

Motivo: Dolor torácico desgarrante; descartar disección aórtica.

Correcto — INDICACIÓN: Mujer de 68 años con dolor torácico desgarrante; descartar disección aórtica.
Correcto — HALLAZGOS: Angio-TC de tórax con opacificación homogénea de arterias pulmonares principales, lobares y segmentarias sin defectos de llenado. Aorta torácica de calibre y contornos conservados, sin flap intimal ni hematoma intramural. Parénquima pulmonar sin consolidaciones, nódulos ni opacidades focales. No hay derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Angio-TC de tórax sin signos de tromboembolismo pulmonar ni de disección aórtica, dentro de límites normales.
Variante — INDICACIÓN: Mujer de 68 años con dolor torácico desgarrante; descartar disección aórtica.
Variante — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado. Aorta torácica de calibre y contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame pleural.
Variante — IMPRESIÓN: Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.
Esperado [doble_chequeo/verify]: body='descartar disección aórtica' impresion='Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.' (Caso de doble chequeo: indicación crítica con plantilla normal que requiere verificación humana y no constituye error.)

- [ ] ✅ / ❌ — comentario:

## B2-0015 · doble_chequeo (verify) — Angio-TC de tórax

Motivo: Dolor torácico desgarrante; descartar disección aórtica.

Correcto — INDICACIÓN: Dolor torácico desgarrante; descartar disección aórtica en mujer de 21 años.
Correcto — HALLAZGOS: Aorta torácica ascendente, arco y descendente de calibre y contornos conservados, sin evidencia de flap intimal, doble luz ni hematoma intramural. Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado sugestivos de tromboembolismo. Parénquima pulmonar sin consolidaciones, opacidades ni nódulos. No hay derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Angio-TC de tórax sin signos de disección aórtica ni tromboembolismo pulmonar.
Variante — INDICACIÓN: Dolor torácico desgarrante; descartar disección aórtica en mujer de 21 años.
Variante — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado. Aorta torácica de calibre y contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame pleural.
Variante — IMPRESIÓN: Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.
Esperado [doble_chequeo/verify]: body='descartar disección aórtica' impresion='' (Estudio con indicación crítica informado con plantilla normal que requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B2-0023 · pregunta (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en fosa ilíaca derecha; descartar apendicitis.

Correcto — INDICACIÓN: Mujer de 50 años con dolor en fosa ilíaca derecha, se solicita TC de abdomen y pelvis con contraste para descartar apendicitis.
Correcto — HALLAZGOS: Apéndice cecal retrocecal de 8 mm de diámetro máximo, con engrosamiento parietal de 3 mm, hipercaptación mucosa y estriación de la grasa periapendicular, hallazgos compatibles con apendicitis aguda. Escaso líquido libre laminar adyacente en fosa ilíaca derecha, sin colecciones ni apendicolito visible. No se evidencian signos de obstrucción intestinal, neumoperitoneo ni lesiones focales hepáticas. Útero y anexos de aspecto usual para la edad, sin masas; vejiga parcialmente distendida sin engrosamientos parietales.
Correcto — IMPRESIÓN: Hallazgos tomográficos compatibles con apendicitis aguda no complicada. No se identifican colecciones ni signos de perforación.
Variante — INDICACIÓN: Mujer de 50 años con dolor en fosa ilíaca derecha, se solicita TC de abdomen y pelvis con contraste para descartar apendicitis.
Variante — HALLAZGOS: Apéndice cecal retrocecal de 8 mm de diámetro máximo, con engrosamiento parietal de 3 mm, hipercaptación mucosa y estriación de la grasa periapendicular, hallazgos compatibles con apendicitis aguda. Escaso líquido libre laminar adyacente en fosa ilíaca derecha, sin colecciones ni apendicolito visible. No se evidencian signos de obstrucción intestinal, neumoperitoneo ni lesiones focales hepáticas. Útero y anexos de aspecto usual para la edad, sin masas; vejiga parcialmente distendida sin engrosamientos parietales.
Variante — IMPRESIÓN: Escaso líquido libre en fosa ilíaca derecha sin colecciones definidas. No se observan signos de obstrucción intestinal.
Esperado [indication_unanswered/error]: body='descartar apendicitis' impresion='' (La indicación pregunta por descartar apendicitis y el cuerpo responde pero la conclusión no la nombra.)

- [ ] ✅ / ❌ — comentario:

## B2-0055 · doble_chequeo (verify) — Angio-TC de tórax

Motivo: Dolor torácico desgarrante; descartar disección aórtica.

Correcto — INDICACIÓN: Hombre de 28 años con dolor torácico desgarrante de inicio súbito para descartar disección aórtica.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación de la aorta torácica y sus ramas principales. Aorta ascendente, cayado y aorta descendente de calibre conservado, sin colgajo intimal ni hematoma intramural, con diámetro máximo de 28 mm en aorta ascendente. Arterias pulmonares principales, lobares y segmentarias permeables sin defectos de llenado. Parénquima pulmonar sin consolidaciones ni opacidades en vidrio esmerilado. No se observa derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Angio-TC de tórax sin evidencia de disección aórtica ni tromboembolismo pulmonar. Aorta torácica de calibre y morfología dentro de límites normales.
Variante — INDICACIÓN: Hombre de 28 años con dolor torácico desgarrante para descartar disección aórtica.
Variante — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado. Aorta torácica de calibre y contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame pleural.
Variante — IMPRESIÓN: Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.
Esperado [doble_chequeo/verify]: body='descartar disección aórtica' impresion='sin tromboembolismo pulmonar ni disección aórtica' (Caso de doble chequeo con indicación crítica de descartar disección aórtica informado con plantilla normal que requiere verificación humana y no constituye error.)

- [ ] ✅ / ❌ — comentario:

## B2-0031 · pregunta (error) — RX de abdomen

Motivo: Estreñimiento crónico; valoración de patrón gaseoso.

Correcto — INDICACIÓN: Hombre de 79 años con estreñimiento crónico para valoración de patrón gaseoso y descartar obstrucción intestinal.
Correcto — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior. Se identifica abundante materia fecal en todo el marco cólico, con fecaloma en ampolla rectal de 5.5 cm de diámetro. No se observa dilatación anormal de asas intestinales ni niveles hidroaéreos sugestivos de obstrucción intestinal. No hay signos de neumoperitoneo ni calcificaciones anormales. Estructuras óseas sin alteraciones agudas.
Correcto — IMPRESIÓN: Abundante carga fecal en marco cólico con fecaloma rectal de 5.5 cm. Sin signos radiológicos de obstrucción intestinal.
Variante — INDICACIÓN: Hombre de 79 años con estreñimiento crónico para valoración de patrón gaseoso y descartar obstrucción intestinal.
Variante — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior. Se identifica abundante materia fecal en todo el marco cólico, con fecaloma en ampolla rectal de 5.5 cm de diámetro. No se observa dilatación anormal de asas intestinales. No hay signos de neumoperitoneo ni calcificaciones anormales. Estructuras óseas sin alteraciones agudas.
Variante — IMPRESIÓN: Abundante carga fecal en marco cólico con fecaloma rectal de 5.5 cm. Patrón gaseoso intestinal sin alteraciones agudas.
Esperado [indication_unanswered/error]: body='descartar obstrucción intestinal' impresion='Patrón gaseoso intestinal sin alteraciones agudas.' (La indicación pregunta por descartar obstrucción intestinal y ni los hallazgos ni la impresión nombran dicha patología.)

- [ ] ✅ / ❌ — comentario:

## B2-0043 · omision (error) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 56 años con dolor torácico y dímero D elevado, remitido para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del árbol arterial pulmonar, sin defectos de llenado en arterias pulmonares principales, lobares, segmentarias ni subsegmentarias. Parénquima pulmonar sin consolidaciones ni infiltrados, sin derrame pleural ni pericárdico. Se identifica nódulo pulmonar sólido de 22 mm en el lóbulo superior derecho, de bordes espiculados, que requiere caracterización adicional y seguimiento por posible etiología neoplásica. Aorta torácica de calibre conservado, sin disección ni aneurisma, corazón y grandes vasos sin alteraciones.
Correcto — IMPRESIÓN: No hay signos de tromboembolismo pulmonar agudo. Nódulo pulmonar sólido espiculado de 22 mm en lóbulo superior derecho, sugestivo de neoplasia, se recomienda correlación con estudios adicionales y valoración por neumología/oncología.
Variante — INDICACIÓN: Hombre de 56 años con dolor torácico y dímero D elevado, remitido para descartar tromboembolismo pulmonar.
Variante — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del árbol arterial pulmonar, sin defectos de llenado en arterias pulmonares principales, lobares, segmentarias ni subsegmentarias. Parénquima pulmonar sin consolidaciones ni infiltrados, sin derrame pleural ni pericárdico. Se identifica nódulo pulmonar sólido de 22 mm en el lóbulo superior derecho, de bordes espiculados, que requiere caracterización adicional y seguimiento por posible etiología neoplásica. Aorta torácica de calibre conservado, sin disección ni aneurisma, corazón y grandes vasos sin alteraciones.
Variante — IMPRESIÓN: No hay signos de tromboembolismo pulmonar agudo. Sin otras alteraciones agudas en tórax.
Esperado [omitted_finding/error]: body='Se identifica nódulo pulmonar sólido de 22 mm en el lóbulo superior derecho, de bordes espiculados, que requiere caracterización adicional y seguimiento por posible etiología neoplásica.' impresion='' (Los HALLAZGOS describen un nódulo pulmonar de 22 mm que requiere seguimiento y la IMPRESIÓN no lo menciona.)

- [ ] ✅ / ❌ — comentario:

## B2-0004 · pregunta (error) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Hombre de 69 años con dolor crónico de rodilla derecha para valoración de cambios degenerativos, descartar gonartrosis severa.
Correcto — HALLAZGOS: Radiografía de rodilla derecha en proyecciones AP y lateral. Se evidencia disminución severa del espacio articular femorotibial medial con esclerosis subcondral y osteofitos marginales de hasta 7 mm. Compartimentos lateral y patelofemoral con pinzamiento leve a moderado y osteofitos pequeños. No hay fractura, luxación ni lesiones óseas agresivas. Tejidos blandos sin edema importante y sin derrame articular evidente.
Correcto — IMPRESIÓN: Gonartrosis tricompartimental severa de predominio femorotibial medial.
Variante — INDICACIÓN: Hombre de 69 años con dolor crónico de rodilla derecha para valoración de cambios degenerativos, descartar gonartrosis severa.
Variante — HALLAZGOS: Radiografía de rodilla derecha en proyecciones AP y lateral. Alineación femorotibial conservada sin evidencia de fractura ni luxación. No se observan lesiones líticas ni blásticas. Tejidos blandos de densidad habitual sin signos de derrame articular evidente.
Variante — IMPRESIÓN: Alineación conservada sin fractura ni luxación.
Esperado [indication_unanswered/error]: body='descartar gonartrosis severa' impresion='Alineación conservada sin fractura ni luxación.' (La indicación pregunta por descartar gonartrosis severa y ni los hallazgos ni la impresión mencionan gonartrosis ni cambios degenerativos.)

- [ ] ✅ / ❌ — comentario:
