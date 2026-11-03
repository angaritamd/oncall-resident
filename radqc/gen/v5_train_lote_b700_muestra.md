# Bloque 700 train v5 — muestra de revisión (10 casos al azar, semilla 49, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B7-0009 · omision (error) — TC de tórax

Motivo: Control de nódulo pulmonar conocido.

Correcto — INDICACIÓN: TC de tórax para control de nódulo pulmonar conocido en hombre de 67 años.
Correcto — HALLAZGOS: Se observa nódulo pulmonar sólido en el lóbulo superior derecho de 8 mm, estable respecto a control previo, sin cavitación ni calcificaciones asociadas. No se identifican consolidaciones, opacidades en vidrio esmerilado ni derrame pleural significativo. Se identifica adenopatía mediastinal en estación 7 de 16 mm en eje corto, de nueva aparición respecto a estudio previo. Estructuras óseas visualizadas sin lesiones líticas ni blásticas.
Correcto — IMPRESIÓN: Nódulo pulmonar sólido de 8 mm en lóbulo superior derecho, estable sin cambios significativos. Adenopatía mediastinal patológica de 16 mm en estación 7 de nueva aparición que requiere correlación clínica y estudio complementario.
Variante — INDICACIÓN: TC de tórax para control de nódulo pulmonar conocido en hombre de 67 años.
Variante — HALLAZGOS: Se observa nódulo pulmonar sólido en el lóbulo superior derecho de 8 mm, estable respecto a control previo, sin cavitación ni calcificaciones asociadas. No se identifican consolidaciones, opacidades en vidrio esmerilado ni derrame pleural significativo. Se identifica adenopatía mediastinal en estación 7 de 16 mm en eje corto, de nueva aparición respecto a estudio previo. Estructuras óseas visualizadas sin lesiones líticas ni blásticas.
Variante — IMPRESIÓN: Nódulo pulmonar sólido de 8 mm en lóbulo superior derecho, estable sin cambios significativos.
Esperado [omitted_finding/error]: body='adenopatía mediastinal en estación 7 de 16 mm en eje corto, de nueva aparición respecto a estudio previo' impresion='' (HALLAZGOS describe adenopatía mediastinal de 16 mm que requiere estudio adicional y la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B7-0045 · control_pregunta_cuerpo (control) — RX de tórax

Motivo: Tos y fiebre de 5 días; descartar neumonía.

Correcto — INDICACIÓN: Mujer de 82 años con tos y fiebre de 5 días; descartar neumonía y derrame pleural.
Correcto — HALLAZGOS: Radiografía de tórax en proyecciones PA y lateral. No se observan opacidades alveolares ni consolidaciones sugestivas de neumonía. No se evidencia derrame pleural. Silueta cardiomediastínica dentro de límites normales para la edad, sin lesiones óseas agudas visibles.
Correcto — IMPRESIÓN: Sin signos radiológicos de proceso neumónico agudo. Cambios pulmonares involutivos.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B7-0053 · omision (error) — TC de cráneo simple

Motivo: Trauma craneal leve; descartar lesión intracraneal.

Correcto — INDICACIÓN: Hombre de 83 años con trauma craneal leve, estudio de TC de cráneo simple para descartar lesión intracraneal.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de hemorragia intraparenquimatosa, subaracnoidea ni hematomas extraaxiales. No se observan fracturas craneales, con adecuada diferenciación de sustancia gris-blanca y sin desviación de la línea media. Se identifica imagen sacular hiperdensa de 8 mm en el territorio de la arteria comunicante anterior, sugestiva de aneurisma, sin sangrado asociado. Sistema ventricular y cisternas de amplitud normal para la edad, con cambios involutivos ex vacuo y senos paranasales permeables.
Correcto — IMPRESIÓN: TC de cráneo simple sin evidencia de hemorragia aguda ni lesión intracraneal postraumática. Aneurisma sacular de 8 mm en territorio de la arteria comunicante anterior, requiere correlación con angio-TC y valoración por neurocirugía.
Variante — INDICACIÓN: Hombre de 83 años con trauma craneal leve, estudio de TC de cráneo simple para descartar lesión intracraneal.
Variante — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de hemorragia intraparenquimatosa, subaracnoidea ni hematomas extraaxiales. No se observan fracturas craneales, con adecuada diferenciación de sustancia gris-blanca y sin desviación de la línea media. Se identifica imagen sacular hiperdensa de 8 mm en el territorio de la arteria comunicante anterior, sugestiva de aneurisma, sin sangrado asociado. Sistema ventricular y cisternas de amplitud normal para la edad, con cambios involutivos ex vacuo y senos paranasales permeables.
Variante — IMPRESIÓN: TC de cráneo simple sin evidencia de hemorragia aguda ni lesión intracraneal postraumática.
Esperado [omitted_finding/error]: body='Se identifica imagen sacular hiperdensa de 8 mm en el territorio de la arteria comunicante anterior, sugestiva de aneurisma, sin sangrado asociado.' impresion='' (Hallazgo que cambia manejo (aneurisma de 8 mm) descrito en hallazgos y omitido en impresión.)

- [ ] ✅ / ❌ — comentario:

## B7-0015 · pregunta (error) — RX de tórax

Motivo: Tos y fiebre de 5 días; descartar neumonía.

Correcto — INDICACIÓN: Mujer de 55 años con tos y fiebre de 5 días; descartar neumonía.
Correcto — HALLAZGOS: Radiografía de tórax PA y lateral con adecuada técnica inspiratoria. Parénquima pulmonar sin consolidaciones ni opacidades focales sugestivas de neumonía. Silueta cardiomediastinal dentro de límites normales, sin derrame pleural visible. Se observa granuloma calcificado de 5 mm en el lóbulo inferior derecho, sin cambios respecto a estudios previos.
Correcto — IMPRESIÓN: No se observan signos radiológicos de neumonía. Granuloma calcificado estable en base derecha de 5 mm.
Variante — INDICACIÓN: Mujer de 55 años con tos y fiebre de 5 días; descartar neumonía.
Variante — HALLAZGOS: Radiografía de tórax PA y lateral con adecuada técnica inspiratoria. Parénquima pulmonar de aspecto conservado, sin opacidades focales. Silueta cardiomediastinal dentro de límites normales, sin derrame pleural visible. Se observa granuloma calcificado de 5 mm en el lóbulo inferior derecho, sin cambios respecto a estudios previos.
Variante — IMPRESIÓN: Silueta cardiomediastinal dentro de límites normales. Granuloma calcificado estable en base derecha de 5 mm.
Esperado [indication_unanswered/error]: body='descartar neumonía' impresion='Silueta cardiomediastinal dentro de límites normales.' (La indicación solicita descartar neumonía y ni los hallazgos ni la impresión mencionan dicha patología.)

- [ ] ✅ / ❌ — comentario:

## B7-0042 · pregunta (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en fosa ilíaca derecha; descartar apendicitis.

Correcto — INDICACIÓN: Hombre de 68 años con dolor en fosa ilíaca derecha, estudio solicitado para descartar apendicitis.
Correcto — HALLAZGOS: Apéndice cecal de 6 mm de diámetro, con pared delgada, sin hiperrealce parietal ni cambios inflamatorios de la grasa periapendicular. Ciego y última asa ileal sin engrosamiento parietal ni colecciones asociadas. Colon sigmoide con divertículos sin signos de diverticulitis aguda; se identifica quiste cortical renal izquierdo de 18 mm sin septos ni realce interno. No hay adenopatías de tamaño significativo, líquido libre ni uropatía obstructiva.
Correcto — IMPRESIÓN: Apéndice cecal sin signos de apendicitis aguda. Quiste renal izquierdo de 18 mm de aspecto simple (Bosniak I). Diverticulosis sigmoidea no complicada.
Variante — INDICACIÓN: Hombre de 68 años con dolor en fosa ilíaca derecha, estudio solicitado para descartar apendicitis.
Variante — HALLAZGOS: Apéndice cecal de 6 mm de diámetro, con pared delgada, sin hiperrealce parietal ni cambios inflamatorios de la grasa periapendicular. Ciego y última asa ileal sin engrosamiento parietal ni colecciones asociadas. Colon sigmoide con divertículos sin signos de diverticulitis aguda; se identifica quiste cortical renal izquierdo de 18 mm sin septos ni realce interno. No hay adenopatías de tamaño significativo, líquido libre ni uropatía obstructiva.
Variante — IMPRESIÓN: Diverticulosis sigmoidea no complicada. Quiste renal izquierdo de 18 mm de aspecto simple (Bosniak I), sin otros hallazgos de relevancia.
Esperado [indication_unanswered/error]: body='descartar apendicitis' impresion='Diverticulosis sigmoidea no complicada. Quiste renal izquierdo de 18 mm de aspecto simple (Bosniak I), sin otros hallazgos de relevancia.' (La indicación solicita descartar apendicitis, patología crítica, el cuerpo responde pero la conclusión no nombra apéndice ni apendicitis.)

- [ ] ✅ / ❌ — comentario:

## B7-0099 · omision (error) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: Mujer de 65 años en control de litiasis renal conocida.
Correcto — HALLAZGOS: Se identifica calcificación de 7 mm proyectada sobre la silueta renal derecha, compatible con litiasis conocida, sin cambios significativos. Calcificación curvilínea de paredes aórticas con dilatación aneurismática fusiforme de la aorta abdominal infrarrenal de hasta 38 mm de diámetro máximo. Distribución del gas intestinal dentro de límites normales, sin signos de obstrucción ni neumoperitoneo. Estructuras óseas sin lesiones líticas ni blásticas evidentes.
Correcto — IMPRESIÓN: Litiasis renal derecha de 7 mm estable. Dilatación aneurismática fusiforme de la aorta abdominal infrarrenal de 38 mm que requiere valoración por cirugía vascular y angioTC complementaria.
Variante — INDICACIÓN: Mujer de 65 años en control de litiasis renal conocida.
Variante — HALLAZGOS: Se identifica calcificación de 7 mm proyectada sobre la silueta renal derecha, compatible con litiasis conocida, sin cambios significativos. Calcificación curvilínea de paredes aórticas con dilatación aneurismática fusiforme de la aorta abdominal infrarrenal de hasta 38 mm de diámetro máximo. Distribución del gas intestinal dentro de límites normales, sin signos de obstrucción ni neumoperitoneo. Estructuras óseas sin lesiones líticas ni blásticas evidentes.
Variante — IMPRESIÓN: Litiasis renal derecha de 7 mm estable, sin signos de obstrucción intestinal.
Esperado [omitted_finding/error]: body='Calcificación curvilínea de paredes aórticas con dilatación aneurismática fusiforme de la aorta abdominal infrarrenal de hasta 38 mm de diámetro máximo.' impresion='' (La impresión omite la dilatación aneurismática de 38 mm descrita en hallazgos que requiere seguimiento y estudio complementario.)

- [ ] ✅ / ❌ — comentario:

## B7-0072 · control_subrasgos (control) — TC de abdomen y pelvis con contraste

Motivo: Fiebre posoperatoria; descartar colección.

Correcto — INDICACIÓN: Mujer de 71 años con fiebre posoperatoria, TC de abdomen y pelvis con contraste para descartar colección.
Correcto — HALLAZGOS: Vesícula biliar distendida que mide 42 mm en diámetro transverso con engrosamiento parietal de 7 mm e hipercaptación de la pared tras el contraste. Cálculo hiperdenso impactado en el cuello vesicular de 13 mm asociado a líquido pericolecístico y edema perivesicular. No se identifican colecciones intraabdominales ni líquido libre en pelvis. Hígado, bazo, páncreas, riñones y estructuras intestinales sin alteraciones agudas, sin signos de obstrucción ni neumoperitoneo.
Correcto — IMPRESIÓN: Colecistitis aguda litiásica con engrosamiento parietal y líquido pericolecístico. Sin colecciones intraabdominales.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B7-0067 · omision (error) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Mujer de 33 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Correcto — HALLAZGOS: Rodilla con adecuada alineación femorotibial y femoropatelar sin alteraciones de la densidad ósea. Se observan cambios degenerativos incipientes con leve esclerosis subcondral y pequeños osteofitos marginales en el compartimento femorotibial medial. Se identifica derrame articular moderado con distensión líquida de la bursa suprarrotuliana de 24 mm de espesor máximo. No se evidencian fracturas, luxaciones ni lesiones óseas agresivas.
Correcto — IMPRESIÓN: Cambios degenerativos incipientes del compartimento femorotibial medial. Derrame articular moderado de 24 mm que requiere correlación clínica y estudio complementario.
Variante — INDICACIÓN: Mujer de 33 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Variante — HALLAZGOS: Rodilla con adecuada alineación femorotibial y femoropatelar sin alteraciones de la densidad ósea. Se observan cambios degenerativos incipientes con leve esclerosis subcondral y pequeños osteofitos marginales en el compartimento femorotibial medial. Se identifica derrame articular moderado con distensión líquida de la bursa suprarrotuliana de 24 mm de espesor máximo. No se evidencian fracturas, luxaciones ni lesiones óseas agresivas.
Variante — IMPRESIÓN: Cambios degenerativos incipientes del compartimento femorotibial medial sin lesiones óseas agudas.
Esperado [omitted_finding/error]: body='Se identifica derrame articular moderado con distensión líquida de la bursa suprarrotuliana de 24 mm de espesor máximo.' impresion='' (HALLAZGOS describe derrame articular de 24 mm que cambia el manejo y la IMPRESIÓN lo omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B7-0007 · control_limitacion (control) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Hombre de 87 años con derrame articular de rodilla, para descartar lesión ósea.
Correcto — HALLAZGOS: Se realizan proyecciones anteroposterior y lateral de rodilla derecha con adecuada técnica. Se observa derrame articular suprapatelar con distensión de la bursa de aproximadamente 18 mm de espesor. Cambios degenerativos tricompartimentales con osteofitos marginales de hasta 6 mm y estrechamiento femorotibial medial moderado. No se identifican trazos de fractura ni lesiones líticas o blásticas; osteopenia difusa y calcificación vascular poplítea de 12 mm.
Correcto — IMPRESIÓN: No se identifica lesión ósea aguda; evaluación limitada por osteopenia marcada y derrame articular denso. Derrame articular suprapatelar persistente de 18 mm y gonartrosis tricompartimental.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B7-0089 · omision (error) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Mujer de 35 años con dolor torácico agudo y dímero D elevado, estudio solicitado para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del tronco y ramas principales de las arterias pulmonares, sin defectos de llenado compatibles con tromboembolismo pulmonar agudo. Se identifica dilatación aneurismática de la aorta ascendente que mide 44 mm de diámetro máximo. Parénquima pulmonar sin consolidaciones ni infiltrados, sin derrame pleural significativo. No se observan adenopatías mediastinales patológicas.
Correcto — IMPRESIÓN: No hay signos de tromboembolismo pulmonar agudo. Aneurisma de la aorta ascendente de 44 mm, se sugiere valoración por cirugía vascular y control por imágenes.
Variante — INDICACIÓN: Mujer de 35 años con dolor torácico agudo y dímero D elevado, estudio solicitado para descartar tromboembolismo pulmonar.
Variante — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del tronco y ramas principales de las arterias pulmonares, sin defectos de llenado compatibles con tromboembolismo pulmonar agudo. Se identifica dilatación aneurismática de la aorta ascendente que mide 44 mm de diámetro máximo. Parénquima pulmonar sin consolidaciones ni infiltrados, sin derrame pleural significativo. No se observan adenopatías mediastinales patológicas.
Variante — IMPRESIÓN: No se identifican defectos de llenado compatibles con tromboembolismo pulmonar agudo.
Esperado [omitted_finding/error]: body='dilatación aneurismática de la aorta ascendente que mide 44 mm de diámetro máximo' impresion='' (Los HALLAZGOS describen una dilatación aneurismática de la aorta ascendente de 44 mm que cambia el manejo y requiere seguimiento, hallazgo que la IMPRESIÓN de la variante omite por completo.)

- [ ] ✅ / ❌ — comentario:
