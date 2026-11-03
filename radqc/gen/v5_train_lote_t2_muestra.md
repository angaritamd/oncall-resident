# Tanda 2 train v5 (primeros 100) — muestra de revisión (10 casos al azar, semilla 42, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## T2-0083 · pregunta (error) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Mujer de 23 años con derrame articular de rodilla derecha, se solicita descartar lesión ósea.
Correcto — HALLAZGOS: Radiografía de rodilla derecha en proyecciones anteroposterior y lateral. Se observa aumento de densidad en el receso suprapatelar compatible con derrame articular, con distensión capsular de 14 mm. No se identifican lesiones líticas, blásticas ni trazos de fractura; la cortical y la trabeculación ósea se preservan. Espacios articulares femorotibial y femoropatelar conservados, sin cuerpos libres calcificados.
Correcto — IMPRESIÓN: Derrame articular moderado de la rodilla derecha. Sin evidencia de lesión ósea.
Variante — INDICACIÓN: Mujer de 23 años con derrame articular de rodilla derecha, se solicita descartar lesión ósea.
Variante — HALLAZGOS: Radiografía de rodilla derecha en proyecciones anteroposterior y lateral. Se observa aumento de densidad en el receso suprapatelar compatible con derrame articular, con distensión capsular de 14 mm. Espacios articulares femorotibial y femoropatelar conservados, sin cuerpos libres calcificados.
Variante — IMPRESIÓN: Derrame articular moderado de la rodilla derecha.
Esperado [indication_unanswered/error]: body='descartar lesión ósea' impresion='' (La indicación pregunta por descartar lesión ósea (no crítica) y ni hallazgos ni impresión la responden.)

- [ ] ✅ / ❌ — comentario:

## T2-0015 · pregunta (error) — TC de tórax

Motivo: Estadificación de neoplasia conocida.

Correcto — INDICACIÓN: Mujer de 28 años con neoplasia conocida para estadificación, descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: TC de tórax contrastado sin artefactos que limiten la evaluación. Se identifica nódulo sólido de 12 mm en el lóbulo inferior derecho sin cavitación ni calcificaciones. No se observan defectos de llenado en el tronco de la arteria pulmonar ni en sus ramas principales y segmentarias, sin signos de tromboembolismo pulmonar. No hay adenopatías mediastinales significativas ni derrame pleural.
Correcto — IMPRESIÓN: Nódulo sólido de 12 mm en lóbulo inferior derecho sugestivo de metástasis pulmonar. Sin evidencia de tromboembolismo pulmonar.
Variante — INDICACIÓN: Mujer de 28 años con neoplasia conocida para estadificación, descartar tromboembolismo pulmonar.
Variante — HALLAZGOS: TC de tórax contrastado sin artefactos que limiten la evaluación. Se identifica nódulo sólido de 12 mm en el lóbulo inferior derecho sin cavitación ni calcificaciones. No se observan defectos de llenado en el tronco de la arteria pulmonar ni en sus ramas principales y segmentarias, sin signos de tromboembolismo pulmonar. No hay adenopatías mediastinales significativas ni derrame pleural.
Variante — IMPRESIÓN: Nódulo sólido de 12 mm en lóbulo inferior derecho sugestivo de metástasis pulmonar. Parénquima pulmonar sin consolidaciones.
Esperado [indication_unanswered/error]: body='descartar tromboembolismo pulmonar' impresion='Parénquima pulmonar sin consolidaciones.' (La indicación pregunta por descartar tromboembolismo pulmonar, el cuerpo responde pero la conclusión no.)

- [ ] ✅ / ❌ — comentario:

## T2-0004 · pregunta (error) — TC de tórax

Motivo: Tos crónica y pérdida de peso; descartar neoplasia.

Correcto — INDICACIÓN: Hombre de 84 años con tos crónica y pérdida de peso; TC de tórax para descartar neoplasia pulmonar.
Correcto — HALLAZGOS: Parénquima pulmonar con enfisema centrolobulillar y tractos fibrosos bibasales, sin consolidaciones ni masas visibles. No se identifican nódulos pulmonares ni lesiones endobronquiales sospechosas de neoplasia; tráquea y bronquios principales permeables. Ganglio prevascular de 9 mm sin criterios adenomegálicos; no hay derrame pleural ni pericárdico. Estructuras óseas sin lesiones líticas ni blásticas; aorta torácica ateromatosa sin aneurisma.
Correcto — IMPRESIÓN: Cambios enfisematosos y fibrosis bibasal sin evidencia de proceso neoplásico pulmonar. Adenopatía mediastinal inespecífica de 9 mm sin otros hallazgos sospechosos.
Variante — INDICACIÓN: Hombre de 84 años con tos crónica y pérdida de peso; TC de tórax para descartar neoplasia pulmonar.
Variante — HALLAZGOS: Parénquima pulmonar con enfisema centrolobulillar y tractos fibrosos bibasales. Tráquea y bronquios principales permeables sin lesiones endoluminales. Ganglio prevascular de 9 mm sin criterios adenomegálicos; no hay derrame pleural ni pericárdico. Estructuras óseas sin lesiones líticas ni blásticas; aorta torácica ateromatosa sin aneurisma.
Variante — IMPRESIÓN: Cambios enfisematosos y fibrosis bibasal. Adenopatía mediastinal inespecífica de 9 mm.
Esperado [indication_unanswered/error]: body='descartar neoplasia pulmonar' impresion='' (Pregunta no crítica 'descartar neoplasia pulmonar' en indicación sin respuesta en hallazgos ni en impresión.)

- [ ] ✅ / ❌ — comentario:

## T2-0097 · control_subrasgos (control) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 72 años con dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con contraste en fase arterial pulmonar con adecuada opacificación del tronco y ramas principales, sin defectos de llenado compatibles con tromboembolismo pulmonar. En los cortes bajos que incluyen el hipocondrio derecho se visualiza parcialmente la vesícula biliar con engrosamiento parietal de 5 mm. Se observa líquido pericolecístico laminar y leve densificación de la grasa adyacente. En su interior se identifica cálculo hiperdenso de 12 mm impactado en el cuello vesicular. Parénquima pulmonar sin consolidaciones; aorta torácica sin flap intimal; sin derrame pleural ni adenopatías mediastinales significativas.
Correcto — IMPRESIÓN: Sin evidencia de tromboembolismo pulmonar agudo. Hallazgos compatibles con colecistitis aguda litiásica, con engrosamiento parietal de 5 mm y cálculo de 12 mm; se sugiere correlación clínica y valoración por cirugía.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T2-0036 · omision (error) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Hombre de 19 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Correcto — HALLAZGOS: Radiografías AP y lateral de rodilla derecha con adecuada exposición y sin artefactos. Se observa leve esclerosis subcondral en compartimento femorotibial medial con pinzamiento articular incipiente y sin osteofitos significativos. En la metáfisis distal del fémur, excéntrica y cortical, se identifica lesión lítica de 32 mm con borde esclerótico bien definido y sin reacción perióstica agresiva. No hay fractura, luxación ni derrame articular significativo.
Correcto — IMPRESIÓN: Cambios degenerativos incipientes del compartimento femorotibial medial. Lesión lítica de 32 mm en metáfisis distal del fémur de aspecto benigno, probablemente fibroma no osificante; se recomienda correlación con RM para caracterización y seguimiento.
Variante — INDICACIÓN: Hombre de 19 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Variante — HALLAZGOS: Radiografías AP y lateral de rodilla derecha con adecuada exposición y sin artefactos. Se observa leve esclerosis subcondral en compartimento femorotibial medial con pinzamiento articular incipiente y sin osteofitos significativos. En la metáfisis distal del fémur, excéntrica y cortical, se identifica lesión lítica de 32 mm con borde esclerótico bien definido y sin reacción perióstica agresiva. No hay fractura, luxación ni derrame articular significativo.
Variante — IMPRESIÓN: Cambios degenerativos incipientes del compartimento femorotibial medial sin fractura ni otras alteraciones agudas.
Esperado [omitted_finding/error]: body='lesión lítica de 32 mm con borde esclerótico bien definido' impresion='' (Los hallazgos describen una lesión lítica de 32 mm que requiere estudio adicional y seguimiento pero la impresión la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## T2-0032 · control_limitacion (control) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Mujer de 61 años con derrame articular de rodilla, remitida para descartar lesión ósea.
Correcto — HALLAZGOS: Estudio de rodilla en proyecciones anteroposterior y lateral. Se observa derrame articular suprapatelar moderado con distensión del receso articular. Cambios osteoartrósicos femorotibiales con osteofitos marginales de hasta 7 mm y disminución del espacio articular medial. No se identifican trazos de fractura ni lesiones óseas líticas o blásticas.
Correcto — IMPRESIÓN: No se identifica lesión ósea franca en las proyecciones obtenidas; evaluación del platillo tibial limitada por el derrame articular y la osteopenia. Derrame articular suprapatelar moderado asociado a gonartrosis.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T2-0029 · pregunta (error) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Hombre de 78 años con derrame articular de rodilla izquierda, se solicita radiografía para descartar lesión ósea.
Correcto — HALLAZGOS: Radiografía de rodilla izquierda en proyecciones anteroposterior y lateral. Se evidencia derrame articular moderado con distensión del receso suprapatelar. No se observan lesiones óseas líticas, blásticas ni fracturas. Gonartrosis tricompartimental severa con osteofitos marginales de hasta 8 mm y esclerosis subcondral. Alineación conservada sin luxación.
Correcto — IMPRESIÓN: Gonartrosis severa con derrame articular moderado. No se identifica lesión ósea.
Variante — INDICACIÓN: Hombre de 78 años con derrame articular de rodilla izquierda, se solicita radiografía para descartar lesión ósea.
Variante — HALLAZGOS: Radiografía de rodilla izquierda en proyecciones anteroposterior y lateral. Se evidencia derrame articular moderado con distensión del receso suprapatelar. Gonartrosis tricompartimental severa con osteofitos marginales de hasta 8 mm y esclerosis subcondral. Alineación conservada sin luxación.
Variante — IMPRESIÓN: Gonartrosis tricompartimental severa con derrame articular moderado. Cambios degenerativos crónicos.
Esperado [indication_unanswered/error]: body='descartar lesión ósea' impresion='' (La indicación pregunta por descartar lesión ósea y ni los hallazgos ni la impresión la responden.)

- [ ] ✅ / ❌ — comentario:

## T2-0018 · control_menores (control) — RX de rodilla

Motivo: Trauma en rodilla; descartar fractura.

Correcto — INDICACIÓN: Mujer de 39 años con trauma en rodilla, estudio solicitado para descartar fractura.
Correcto — HALLAZGOS: No se identifican trazos de fractura ni luxación. La alineación femorotibial y femoropatelar se encuentra conservada con densidad ósea normal. Se observan cambios degenerativos leves en el compartimento femorotibial medial con pequeño osteofito marginal de 2 mm. No hay derrame articular significativo ni alteraciones de las partes blandas.
Correcto — IMPRESIÓN: No se observan signos de fractura ni luxación.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T2-0014 · doble_chequeo (verify) — TC de cráneo simple

Motivo: Déficit neurológico súbito; descartar hemorragia intracraneal.

Correcto — INDICACIÓN: Mujer de 36 años con déficit neurológico súbito, se solicita TC de cráneo simple para descartar hemorragia intracraneal.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de hemorragia intraparenquimatosa, subaracnoidea ni extraaxial. Sistema ventricular de amplitud normal, sin hidrocefalia ni colecciones. Cisternas basales permeables y surcos corticales conservados. Línea media centrada, sin desviación ni efecto de masa. Estructuras óseas sin trazos de fractura.
Correcto — IMPRESIÓN: No se identifica hemorragia intracraneal. TC de cráneo simple sin alteraciones agudas.
Variante — INDICACIÓN: Mujer de 36 años con déficit neurológico súbito, se solicita TC de cráneo simple para descartar hemorragia intracraneal.
Variante — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Variante — IMPRESIÓN: TC de cráneo simple sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar hemorragia intracraneal' impresion='TC de cráneo simple sin alteraciones agudas.' (Es caso de doble chequeo con plantilla normal: el cuerpo responde pero la conclusión no nombra explícitamente la hemorragia intracraneal y requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## T2-0088 · pregunta (error) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Hombre de 80 años con derrame articular de rodilla, se solicita descartar lesión ósea.
Correcto — HALLAZGOS: Se observa aumento de la densidad en el receso suprapatelar compatible con derrame articular moderado. Cambios degenerativos femorotibiales con osteofitos marginales de hasta 5 mm y disminución del espacio articular medial. No se identifican lesiones óseas líticas, blásticas ni trazos de fractura. Alineación conservada sin alteraciones de partes blandas adyacentes.
Correcto — IMPRESIÓN: Derrame articular moderado de rodilla. Cambios osteoartrósicos moderados. Sin evidencia de lesión ósea.
Variante — INDICACIÓN: Hombre de 80 años con derrame articular de rodilla, se solicita descartar lesión ósea.
Variante — HALLAZGOS: Se observa aumento de la densidad en el receso suprapatelar compatible con derrame articular moderado. Cambios degenerativos femorotibiales con osteofitos marginales de hasta 5 mm y disminución del espacio articular medial. Esclerosis subcondral en meseta tibial medial. Alineación conservada sin alteraciones de partes blandas adyacentes.
Variante — IMPRESIÓN: Derrame articular moderado de rodilla. Cambios osteoartrósicos moderados.
Esperado [indication_unanswered/error]: body='descartar lesión ósea' impresion='' (La pregunta no crítica descartar lesión ósea no es respondida ni en hallazgos ni en impresión.)

- [ ] ✅ / ❌ — comentario:
