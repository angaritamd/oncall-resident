# Bloque 400 train v5 — muestra de revisión (10 casos al azar, semilla 46, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B4-0014 · doble_chequeo (verify) — TC de abdomen y pelvis con contraste

Motivo: Trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.

Correcto — INDICACIÓN: Mujer de 27 años con trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.
Correcto — HALLAZGOS: Hígado, bazo, páncreas y riñones de morfología, tamaño y realce conservados, sin laceraciones ni hematomas. No se identifica líquido libre intraperitoneal ni retroperitoneal ni signos de sangrado activo. Vesícula biliar, vía biliar y vejiga sin alteraciones. No hay neumoperitoneo, colecciones ni lesiones óseas agudas evidentes.
Correcto — IMPRESIÓN: No se identifican signos de lesión de víscera sólida ni de hemorragia intraabdominal. TC de abdomen y pelvis sin alteraciones agudas.
Variante — INDICACIÓN: Mujer de 27 años con trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.
Variante — HALLAZGOS: Hígado, bazo, páncreas, glándulas suprarrenales y riñones de tamaño y realce normales. Sin apendicolito ni engrosamiento apendicular. Vesícula biliar sin litiasis. Sin colecciones ni líquido libre.
Variante — IMPRESIÓN: TC de abdomen y pelvis sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar lesión de víscera sólida' impresion='TC de abdomen y pelvis sin alteraciones agudas.' (Caso de doble chequeo con pregunta crítica de lesión de víscera sólida en la indicación informado con plantilla normal que requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B4-0061 · doble_chequeo (verify) — TC de cráneo simple

Motivo: Déficit neurológico súbito; descartar hemorragia intracraneal.

Correcto — INDICACIÓN: Mujer de 26 años con déficit neurológico súbito; descartar hemorragia intracraneal.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin focos de sangrado intra o extraaxial ni signos de efecto de masa. Sistema ventricular y cisternas de tamaño y morfología normales. Línea media centrada sin desviaciones. No se observan fracturas ni alteraciones óseas agudas.
Correcto — IMPRESIÓN: TC de cráneo simple sin evidencia de hemorragia intracraneal. No se observan otras alteraciones agudas intracraneales.
Variante — INDICACIÓN: Mujer de 26 años con déficit neurológico súbito; descartar hemorragia intracraneal.
Variante — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Variante — IMPRESIÓN: TC de cráneo simple sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar hemorragia intracraneal' impresion='TC de cráneo simple sin alteraciones agudas.' (Caso de doble chequeo con motivo crítico explícito en la indicación e informe con plantilla normal que requiere verificación humana y no constituye error.)

- [ ] ✅ / ❌ — comentario:

## B4-0010 · control_subrasgos (control) — TC de cráneo simple

Motivo: Cefalea crónica de reciente cambio de patrón.

Correcto — INDICACIÓN: Mujer de 49 años con cefalea crónica de reciente cambio de patrón.
Correcto — HALLAZGOS: Se identifica lesión extraaxial frontal parasagital derecha, bien delimitada, isodensa a discretamente hiperdensa, de 34 mm en su diámetro mayor. Asocia calcificaciones puntiformes internas e hiperostosis de la tabla interna adyacente. Genera edema vasogénico perilesional moderado y efecto de masa con desplazamiento de la línea media de 4 mm hacia la izquierda. Sistema ventricular, cisternas y surcos de morfología conservada, sin evidencia de hemorragia intra o extraaxial ni hidrocefalia.
Correcto — IMPRESIÓN: Lesión extraaxial frontal parasagital derecha de 34 mm compatible con meningioma, con edema perilesional y desplazamiento de la línea media de 4 mm. Sin signos de hemorragia intracraneal aguda.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B4-0087 · control_menores (control) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 45 años con dolor torácico y dímero D elevado, se solicita angio-TC de tórax para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con contraste intravenoso con adecuada opacificación del árbol arterial pulmonar sin defectos de llenado en arterias pulmonares principales, lobares, segmentarias ni subsegmentarias. Parénquima pulmonar sin consolidaciones, sin derrame pleural ni neumotórax. Aorta torácica sin signos de disección, mediastino sin adenopatías y corazón sin alteraciones agudas. Cambios espondilósicos leves en columna dorsal con osteofitos marginales anteriores.
Correcto — IMPRESIÓN: Angio-TC de tórax sin evidencia de tromboembolismo pulmonar agudo ni otros hallazgos agudos.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B4-0036 · omision (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en fosa ilíaca derecha; descartar apendicitis.

Correcto — INDICACIÓN: Mujer de 41 años con dolor en fosa ilíaca derecha; descartar apendicitis.
Correcto — HALLAZGOS: Apéndice cecal de 6 mm de diámetro, sin engrosamiento parietal ni cambios inflamatorios periapendiculares. No se observa líquido libre ni colecciones en fosa ilíaca derecha. Se identifica masa anexial derecha compleja, heterogénea, de 52 mm, con componente sólido y septos gruesos, que requiere correlación ginecológica y caracterización adicional. Hígado, bazo, páncreas y riñones sin lesiones focales, sin adenopatías significativas ni lesiones óseas agresivas.
Correcto — IMPRESIÓN: Apéndice cecal sin signos de apendicitis aguda. Masa anexial derecha compleja de 52 mm, de aspecto sospechoso, requiere valoración ginecológica y resonancia magnética pélvica para caracterización.
Variante — INDICACIÓN: Mujer de 41 años con dolor en fosa ilíaca derecha; descartar apendicitis.
Variante — HALLAZGOS: Apéndice cecal de 6 mm de diámetro, sin engrosamiento parietal ni cambios inflamatorios periapendiculares. No se observa líquido libre ni colecciones en fosa ilíaca derecha. Se identifica masa anexial derecha compleja, heterogénea, de 52 mm, con componente sólido y septos gruesos, que requiere correlación ginecológica y caracterización adicional. Hígado, bazo, páncreas y riñones sin lesiones focales, sin adenopatías significativas ni lesiones óseas agresivas.
Variante — IMPRESIÓN: Apéndice cecal sin signos de apendicitis aguda, sin hallazgos inflamatorios agudos en fosa ilíaca derecha.
Esperado [omitted_finding/error]: body='Se identifica masa anexial derecha compleja, heterogénea, de 52 mm, con componente sólido y septos gruesos, que requiere correlación ginecológica y caracterización adicional.' impresion='' (La impresión omite la masa anexial derecha compleja de 52 mm descrita en hallazgos que requiere estudio adicional y cambia el manejo.)

- [ ] ✅ / ❌ — comentario:

## B4-0093 · doble_chequeo (verify) — Angio-TC de tórax

Motivo: Dolor torácico desgarrante; descartar disección aórtica.

Correcto — INDICACIÓN: Hombre de 86 años con dolor torácico desgarrante; descartar disección aórtica.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del árbol arterial pulmonar hasta ramas segmentarias, sin defectos de llenado. Aorta torácica de calibre conservado, contornos regulares, sin flap intimal ni hematoma intramural. Parénquima pulmonar sin consolidaciones ni opacidades focales. No hay derrame pleural ni pericárdico.
Correcto — IMPRESIÓN: Angio-TC de tórax sin evidencia de tromboembolismo pulmonar ni disección aórtica. No se observan hallazgos agudos adicionales.
Variante — INDICACIÓN: Hombre de 86 años con dolor torácico desgarrante; descartar disección aórtica.
Variante — HALLAZGOS: Arterias pulmonares principales, lobares y segmentarias opacificadas de forma homogénea, sin defectos de llenado. Aorta torácica de calibre y contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame pleural.
Variante — IMPRESIÓN: Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.
Esperado [doble_chequeo/verify]: body='descartar disección aórtica' impresion='Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.' (Estudio con indicación crítica informado con plantilla normal; requiere verificación humana y no constituye error de interpretación.)

- [ ] ✅ / ❌ — comentario:

## B4-0077 · pregunta (error) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: Control de litiasis renal conocida para descartar litiasis residual.
Correcto — HALLAZGOS: Radiografía de abdomen con adecuada técnica y penetración. Se identifica imagen radiopaca de 7 mm en polo inferior del riñón derecho compatible con litiasis. No se observan otras calcificaciones en trayecto ureteral ni en vejiga. Distribución de gas intestinal y silueta de psoas dentro de límites normales.
Correcto — IMPRESIÓN: Litiasis renal derecha de 7 mm en polo inferior, sin cambios significativos.
Variante — INDICACIÓN: Control de litiasis renal conocida para descartar litiasis residual.
Variante — HALLAZGOS: Radiografía de abdomen con adecuada técnica y penetración. Silueta renal y contornos del psoas de aspecto conservado. Trayecto ureteral y silueta vesical sin alteraciones evidentes. Distribución de gas intestinal dentro de límites normales.
Variante — IMPRESIÓN: Estudio dentro de límites normales.
Esperado [indication_unanswered/error]: body='descartar litiasis residual' impresion='Estudio dentro de límites normales.' (La indicación interroga por litiasis residual y ni los hallazgos ni la impresión la responden.)

- [ ] ✅ / ❌ — comentario:

## B4-0025 · pregunta (error) — RX de tórax

Motivo: Tos y fiebre de 5 días; descartar neumonía.

Correcto — INDICACIÓN: Hombre de 44 años con tos y fiebre de 5 días; descartar neumonía.
Correcto — HALLAZGOS: Radiografía de tórax PA y lateral con adecuada inspiración y sin artefactos. Silueta cardiomediastínica de tamaño y contorno conservados. No se observan opacidades alveolares, consolidaciones ni derrame pleural sugestivos de neumonía. Estructuras óseas y tejidos blandos sin alteraciones significativas.
Correcto — IMPRESIÓN: No hay hallazgos radiológicos de neumonía. Estudio sin alteraciones agudas cardiopulmonares.
Variante — INDICACIÓN: Hombre de 44 años con tos y fiebre de 5 días; descartar neumonía.
Variante — HALLAZGOS: Radiografía de tórax PA y lateral con adecuada inspiración y sin artefactos. Silueta cardiomediastínica de tamaño y contorno conservados. Parénquima pulmonar con trama broncovascular conservada y ángulos costofrénicos libres. Estructuras óseas y tejidos blandos sin alteraciones significativas.
Variante — IMPRESIÓN: Estudio dentro de límites normales, sin alteraciones agudas visibles.
Esperado [indication_unanswered/error]: body='descartar neumonía' impresion='Estudio dentro de límites normales, sin alteraciones agudas visibles.' (Pregunta no crítica 'descartar neumonía' queda sin respuesta ni en hallazgos ni en impresión.)

- [ ] ✅ / ❌ — comentario:

## B4-0086 · omision (error) — RX de abdomen

Motivo: Distensión y vómito; descartar obstrucción intestinal.

Correcto — INDICACIÓN: Mujer de 74 años con distensión abdominal y vómito, estudio solicitado para descartar obstrucción intestinal.
Correcto — HALLAZGOS: Se observa dilatación de asas de intestino delgado en hemiabdomen central con niveles hidroaéreos en proyección de bipedestación, sin evidencia de gas en ampolla rectal. No se identifica neumoperitoneo ni calcificaciones patológicas en topografía ureteral. Se identifica lesión lítica de 32 mm en ala ilíaca derecha con ruptura de cortical y reacción perióstica asociada. Resto de estructuras óseas sin alteraciones agudas y silueta hepática y renal dentro de límites normales para la técnica.
Correcto — IMPRESIÓN: Hallazgos compatibles con obstrucción intestinal de intestino delgado sin signos de perforación. Lesión lítica agresiva de 32 mm en ala ilíaca derecha, se sugiere correlación con TC de pelvis y valoración por ortopedia oncológica.
Variante — INDICACIÓN: Mujer de 74 años con distensión abdominal y vómito, estudio solicitado para descartar obstrucción intestinal.
Variante — HALLAZGOS: Se observa dilatación de asas de intestino delgado en hemiabdomen central con niveles hidroaéreos en proyección de bipedestación, sin evidencia de gas en ampolla rectal. No se identifica neumoperitoneo ni calcificaciones patológicas en topografía ureteral. Se identifica lesión lítica de 32 mm en ala ilíaca derecha con ruptura de cortical y reacción perióstica asociada. Resto de estructuras óseas sin alteraciones agudas y silueta hepática y renal dentro de límites normales para la técnica.
Variante — IMPRESIÓN: Hallazgos compatibles con obstrucción intestinal de intestino delgado sin signos de perforación.
Esperado [omitted_finding/error]: body='Se identifica lesión lítica de 32 mm en ala ilíaca derecha con ruptura de cortical y reacción perióstica asociada.' impresion='' (HALLAZGOS describe lesión lítica agresiva de 32 mm que requiere estudio adicional y cambia el manejo, omitida en la IMPRESIÓN.)

- [ ] ✅ / ❌ — comentario:

## B4-0079 · omision (error) — RX de rodilla

Motivo: Trauma en rodilla; descartar fractura.

Correcto — INDICACIÓN: Mujer de 46 años con trauma en rodilla derecha, radiografía solicitada para descartar fractura.
Correcto — HALLAZGOS: Radiografía de rodilla derecha en proyecciones anteroposterior y lateral. No se observan trazos de fractura ni luxación, con alineación conservada. Se identifica lesión lítica de 32 mm en metáfisis distal del fémur, de bordes irregulares y reacción perióstica lamelar, con matriz heterogénea. Moderado derrame articular y cambios degenerativos femorotibiales leves con esclerosis subcondral.
Correcto — IMPRESIÓN: No hay evidencia de fractura aguda. Lesión lítica de 32 mm en fémur distal de características agresivas que requiere correlación con resonancia magnética y valoración por ortopedia oncológica.
Variante — INDICACIÓN: Mujer de 46 años con trauma en rodilla derecha, radiografía solicitada para descartar fractura.
Variante — HALLAZGOS: Radiografía de rodilla derecha en proyecciones anteroposterior y lateral. No se observan trazos de fractura ni luxación, con alineación conservada. Se identifica lesión lítica de 32 mm en metáfisis distal del fémur, de bordes irregulares y reacción perióstica lamelar, con matriz heterogénea. Moderado derrame articular y cambios degenerativos femorotibiales leves con esclerosis subcondral.
Variante — IMPRESIÓN: No se identifica fractura aguda. Cambios degenerativos leves y derrame articular moderado.
Esperado [omitted_finding/error]: body='Se identifica lesión lítica de 32 mm en metáfisis distal del fémur, de bordes irregulares y reacción perióstica lamelar, con matriz heterogénea.' impresion='' (HALLAZGOS describe lesión lítica agresiva de 32 mm que requiere estudio adicional y la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:
