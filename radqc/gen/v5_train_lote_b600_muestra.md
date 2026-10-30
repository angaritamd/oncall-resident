# Bloque 600 train v5 — muestra de revisión (10 casos al azar, semilla 48, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B6-0079 · omision (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en hipocondrio derecho; descartar colecistitis.

Correcto — INDICACIÓN: TC de abdomen y pelvis con contraste en mujer de 76 años con dolor en hipocondrio derecho; descartar colecistitis.
Correcto — HALLAZGOS: Vesícula biliar distendida con engrosamiento parietal de 5 mm y discreto líquido perivesicular, sin cálculos hiperdensos evidentes. Vía biliar intra y extrahepática sin dilatación. Aneurisma fusiforme de la aorta abdominal infrarrenal de 43 mm de diámetro máximo, sin signos de ruptura ni hematoma periaórtico. Páncreas, bazo, riñones y vejiga sin alteraciones relevantes. No hay adenopatías significativas, colecciones ni signos de obstrucción intestinal o neumoperitoneo.
Correcto — IMPRESIÓN: Hallazgos compatibles con colecistitis aguda alitiásica. Aneurisma fusiforme de la aorta abdominal infrarrenal de 43 mm que requiere valoración por cirugía vascular y seguimiento por imágenes.
Variante — INDICACIÓN: TC de abdomen y pelvis con contraste en mujer de 76 años con dolor en hipocondrio derecho; descartar colecistitis.
Variante — HALLAZGOS: Vesícula biliar distendida con engrosamiento parietal de 5 mm y discreto líquido perivesicular, sin cálculos hiperdensos evidentes. Vía biliar intra y extrahepática sin dilatación. Aneurisma fusiforme de la aorta abdominal infrarrenal de 43 mm de diámetro máximo, sin signos de ruptura ni hematoma periaórtico. Páncreas, bazo, riñones y vejiga sin alteraciones relevantes. No hay adenopatías significativas, colecciones ni signos de obstrucción intestinal o neumoperitoneo.
Variante — IMPRESIÓN: Hallazgos compatibles con colecistitis aguda alitiásica. No se observan complicaciones asociadas.
Esperado [omitted_finding/error]: body='Aneurisma fusiforme de la aorta abdominal infrarrenal de 43 mm de diámetro máximo, sin signos de ruptura ni hematoma periaórtico' impresion='' (HALLAZGOS describe aneurisma fusiforme de aorta abdominal de 43 mm que requiere seguimiento y la IMPRESIÓN no lo menciona.)

- [ ] ✅ / ❌ — comentario:

## B6-0046 · omision (error) — RX de rodilla

Motivo: Trauma en rodilla; descartar fractura.

Correcto — INDICACIÓN: Hombre de 82 años con trauma en rodilla, radiografía solicitada para descartar fractura.
Correcto — HALLAZGOS: No se identifican trazos de fractura ni luxación femorotibial o patelofemoral. Cambios osteoartrósicos tricompartimentales con pinzamiento del espacio femorotibial medial y osteofitos marginales de hasta 8 mm. Derrame articular suprapatelar de 18 mm de espesor con nivel líquido-graso sugestivo de lipohemartrosis. Calcificaciones vasculares poplíteas de aspecto aterosclerótico sin alteraciones de partes blandas adicionales.
Correcto — IMPRESIÓN: Gonartrosis tricompartimental sin evidencia de fractura ni luxación. Derrame articular suprapatelar de 18 mm sugestivo de lipohemartrosis que requiere correlación clínica y considerar estudio complementario.
Variante — INDICACIÓN: Hombre de 82 años con trauma en rodilla, radiografía solicitada para descartar fractura.
Variante — HALLAZGOS: No se identifican trazos de fractura ni luxación femorotibial o patelofemoral. Cambios osteoartrósicos tricompartimentales con pinzamiento del espacio femorotibial medial y osteofitos marginales de hasta 8 mm. Derrame articular suprapatelar de 18 mm de espesor con nivel líquido-graso sugestivo de lipohemartrosis. Calcificaciones vasculares poplíteas de aspecto aterosclerótico sin alteraciones de partes blandas adicionales.
Variante — IMPRESIÓN: Gonartrosis tricompartimental sin evidencia de fractura ni luxación.
Esperado [omitted_finding/error]: body='Derrame articular suprapatelar de 18 mm de espesor con nivel líquido-graso sugestivo de lipohemartrosis.' impresion='' (HALLAZGOS describe derrame articular suprapatelar que cambia el manejo y requiere estudio complementario pero la IMPRESIÓN lo omite.)

- [ ] ✅ / ❌ — comentario:

## B6-0019 · control_pregunta_cuerpo (control) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: Control de litiasis renal conocida para descartar obstrucción intestinal crónica.
Correcto — HALLAZGOS: Se observa imagen radiopaca de 8 mm proyectada sobre el polo inferior del riñón derecho compatible con litiasis conocida. No se evidencian signos de obstrucción intestinal ni niveles hidroaéreos patológicos. Distribución del gas intestinal dentro de límites normales sin dilatación anómala de asas. Estructuras óseas visualizadas sin alteraciones evidentes.
Correcto — IMPRESIÓN: Nefrolitiasis derecha de 8 mm estable sin signos de migración ureteral.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B6-0080 · pregunta (error) — RX de abdomen

Motivo: Estreñimiento crónico; valoración de patrón gaseoso.

Correcto — INDICACIÓN: Hombre de 90 años con estreñimiento crónico para valoración del patrón gaseoso, descartar obstrucción intestinal.
Correcto — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior en decúbito supino. Distensión del marco cólico por abundante materia fecal con fecaloma de 7 cm en ampolla rectal. No se identifican signos de obstrucción intestinal, sin dilatación patológica de asas delgadas ni niveles hidroaéreos. No se observa neumoperitoneo ni calcificaciones patológicas.
Correcto — IMPRESIÓN: Abundante retención fecal con fecaloma de 7 cm en ampolla rectal. No hay signos de obstrucción intestinal.
Variante — INDICACIÓN: Hombre de 90 años con estreñimiento crónico para valoración del patrón gaseoso, descartar obstrucción intestinal.
Variante — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior en decúbito supino. Distensión del marco cólico por abundante materia fecal con fecaloma de 7 cm en ampolla rectal. Patrón gaseoso intestinal conservado sin dilatación evidente de asas delgadas. No se observa neumoperitoneo ni calcificaciones patológicas.
Variante — IMPRESIÓN: Abundante retención fecal con fecaloma de 7 cm en ampolla rectal. Patrón gaseoso dentro de límites normales.
Esperado [indication_unanswered/error]: body='descartar obstrucción intestinal' impresion='Abundante retención fecal con fecaloma de 7 cm en ampolla rectal. Patrón gaseoso dentro de límites normales.' (Pregunta no crítica 'descartar obstrucción intestinal' en contexto crónico no es nombrada ni en hallazgos ni en impresión.)

- [ ] ✅ / ❌ — comentario:

## B6-0100 · control_negativos (control) — TC de tórax

Motivo: Estadificación de neoplasia conocida.

Correcto — INDICACIÓN: TC de tórax con contraste para estadificación de neoplasia conocida en mujer de 75 años.
Correcto — HALLAZGOS: Se identifica masa espiculada de 28 mm en el lóbulo superior derecho, compatible con lesión primaria conocida. Múltiples nódulos pulmonares bilaterales, el mayor de 9 mm en el lóbulo inferior izquierdo, sugestivos de compromiso metastásico. Adenopatías mediastinales en estaciones 4R y 7, la mayor de 15 mm en eje corto. No se observa derrame pleural ni pericárdico. Estructuras óseas visualizadas sin lesiones líticas ni blásticas evidentes.
Correcto — IMPRESIÓN: Masa pulmonar en lóbulo superior derecho con nódulos pulmonares bilaterales y adenopatías mediastinales, hallazgos en relación con enfermedad neoplásica conocida. Se sugiere correlación con estudios previos para evaluar progresión.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B6-0077 · pregunta (error) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 39 años con dolor torácico y dímero D elevado, se solicita angio-TC de tórax para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación de las arterias pulmonares hasta ramas segmentarias sin defectos de llenado endoluminales. No se documenta tromboembolismo pulmonar agudo. Parénquima pulmonar sin consolidaciones ni infiltrados. Ganglio mediastinal de 9 mm en estación subcarinal sin características patológicas. No hay derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Sin evidencia de tromboembolismo pulmonar agudo. Sin otros hallazgos agudos en tórax.
Variante — INDICACIÓN: Hombre de 39 años con dolor torácico y dímero D elevado, se solicita angio-TC de tórax para descartar tromboembolismo pulmonar.
Variante — HALLAZGOS: Angio-TC de tórax con adecuada opacificación de las arterias pulmonares hasta ramas segmentarias sin defectos de llenado endoluminales. No se documenta tromboembolismo pulmonar agudo. Parénquima pulmonar sin consolidaciones ni infiltrados. Ganglio mediastinal de 9 mm en estación subcarinal sin características patológicas. No hay derrame pleural ni pericárdico.
Variante — IMPRESIÓN: Parénquima pulmonar sin consolidaciones. No se observan derrames pleurales ni pericárdicos.
Esperado [indication_unanswered/error]: body='descartar tromboembolismo pulmonar' impresion='Parénquima pulmonar sin consolidaciones. No se observan derrames pleurales ni pericárdicos.' (La indicación pregunta por descartar tromboembolismo pulmonar y el cuerpo responde pero la conclusión no nombra la patología crítica.)

- [ ] ✅ / ❌ — comentario:

## B6-0044 · control_negativos (control) — TC de tórax

Motivo: Tos crónica y pérdida de peso; descartar neoplasia.

Correcto — INDICACIÓN: Hombre de 24 años con tos crónica y pérdida de peso para descartar neoplasia.
Correcto — HALLAZGOS: Parénquima pulmonar sin nódulos, masas ni consolidaciones. No se observan adenopatías mediastinales o hiliares significativas. Sin derrame pleural ni neumotórax. Estructuras óseas y tejidos blandos de la pared torácica sin alteraciones.
Correcto — IMPRESIÓN: TC de tórax sin evidencia de lesiones sugestivas de neoplasia.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B6-0073 · doble_chequeo (verify) — TC de abdomen y pelvis con contraste

Motivo: Trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.

Correcto — INDICACIÓN: Hombre de 64 años con trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.
Correcto — HALLAZGOS: Hígado, bazo, páncreas, glándulas suprarrenales y riñones de tamaño, morfología y realce normales, sin laceraciones ni hematomas. No se identifican colecciones hemáticas ni líquido libre intraperitoneal. Intestino delgado, colon y apéndice sin engrosamiento parietal ni signos inflamatorios. Estructuras vasculares abdominales permeables y esqueleto visualizado sin lesiones óseas agudas.
Correcto — IMPRESIÓN: No hay signos de lesión de víscera sólida ni de hemorragia intraabdominal aguda.
Variante — INDICACIÓN: Hombre de 64 años con trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.
Variante — HALLAZGOS: Hígado, bazo, páncreas, glándulas suprarrenales y riñones de tamaño y realce normales. Sin apendicolito ni engrosamiento apendicular. Vesícula biliar sin litiasis. Sin colecciones ni líquido libre.
Variante — IMPRESIÓN: TC de abdomen y pelvis sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar lesión de víscera sólida' impresion='TC de abdomen y pelvis sin alteraciones agudas.' (La indicación plantea descartar lesión de víscera sólida como pregunta crítica y la variante informa plantilla normal genérica sin respuesta explícita, por lo que requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B6-0027 · omision (error) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Hombre de 59 años con derrame articular de rodilla derecha, se solicita radiografía de rodilla para descartar lesión ósea.
Correcto — HALLAZGOS: Rodilla derecha con adecuada alineación sin evidencia de fractura ni lesión ósea aguda. Se observa marcado derrame articular con distensión del receso suprapatelar de 22 mm y aumento de densidad de partes blandas. Cambios degenerativos femorotibiales con osteofitos marginales y leve esclerosis subcondral. No se identifican cuerpos libres ni calcificaciones patológicas.
Correcto — IMPRESIÓN: Sin evidencia de fractura ni lesión ósea aguda. Derrame articular moderado a severo de 22 mm asociado a cambios osteoartrósicos femorotibiales, se sugiere correlación clínica y valorar resonancia magnética para estudio complementario.
Variante — INDICACIÓN: Hombre de 59 años con derrame articular de rodilla derecha, se solicita radiografía de rodilla para descartar lesión ósea.
Variante — HALLAZGOS: Rodilla derecha con adecuada alineación sin evidencia de fractura ni lesión ósea aguda. Se observa marcado derrame articular con distensión del receso suprapatelar de 22 mm y aumento de densidad de partes blandas. Cambios degenerativos femorotibiales con osteofitos marginales y leve esclerosis subcondral. No se identifican cuerpos libres ni calcificaciones patológicas.
Variante — IMPRESIÓN: Sin evidencia de fractura ni lesión ósea aguda. Cambios osteoartrósicos femorotibiales leves sin otras alteraciones.
Esperado [omitted_finding/error]: body='marcado derrame articular con distensión del receso suprapatelar de 22 mm' impresion='' (Los hallazgos describen derrame articular de 22 mm que cambia el manejo y requiere estudio adicional, pero la impresión lo omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B6-0064 · omision (error) — TC de cráneo simple

Motivo: Cefalea crónica de reciente cambio de patrón.

Correcto — INDICACIÓN: Mujer de 38 años con cefalea crónica de reciente cambio de patrón remitida para TC simple de cráneo.
Correcto — HALLAZGOS: Parénquima cerebral supra e infratentorial de densidad conservada, sin lesiones isquémicas ni hemorrágicas evidentes. Sistema ventricular y cisternas de tamaño normal, sin signos de hidrocefalia. Se observa imagen sacular hiperdensa de 7 mm en topografía del segmento supraclinoideo de la carótida interna derecha, sugestiva de aneurisma, que amerita correlación con angioTC. No se identifican colecciones extraaxiales ni efecto de masa. Calota y base de cráneo sin lesiones líticas ni fracturas.
Correcto — IMPRESIÓN: Imagen sacular de 7 mm en carótida interna derecha sugestiva de aneurisma; se recomienda angioTC para caracterización. No se identifica hemorragia intracraneal ni lesión isquémica aguda.
Variante — INDICACIÓN: Mujer de 38 años con cefalea crónica de reciente cambio de patrón remitida para TC simple de cráneo.
Variante — HALLAZGOS: Parénquima cerebral supra e infratentorial de densidad conservada, sin lesiones isquémicas ni hemorrágicas evidentes. Sistema ventricular y cisternas de tamaño normal, sin signos de hidrocefalia. Se observa imagen sacular hiperdensa de 7 mm en topografía del segmento supraclinoideo de la carótida interna derecha, sugestiva de aneurisma, que amerita correlación con angioTC. No se identifican colecciones extraaxiales ni efecto de masa. Calota y base de cráneo sin lesiones líticas ni fracturas.
Variante — IMPRESIÓN: No se identifica hemorragia intracraneal ni lesión isquémica aguda. Resto del estudio dentro de límites normales.
Esperado [omitted_finding/error]: body='Se observa imagen sacular hiperdensa de 7 mm en topografía del segmento supraclinoideo de la carótida interna derecha, sugestiva de aneurisma, que amerita correlación con angioTC.' impresion='' (La impresión omite el aneurisma de 7 mm descrito en hallazgos que requiere estudio adicional.)

- [ ] ✅ / ❌ — comentario:
