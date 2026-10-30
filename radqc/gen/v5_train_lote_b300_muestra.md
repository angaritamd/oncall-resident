# Bloque 300 train v5 — muestra de revisión (10 casos al azar, semilla 45, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B3-0042 · control_limitacion (control) — TC de tórax

Motivo: Control de nódulo pulmonar conocido.

Correcto — INDICACIÓN: Control de nódulo pulmonar conocido.
Correcto — HALLAZGOS: Nódulo pulmonar sólido de 7 mm en el segmento apical del lóbulo superior derecho, estable respecto al estudio previo. No se observan nuevos nódulos, consolidaciones ni opacidades en vidrio esmerilado. No hay derrame pleural ni adenopatías mediastinales significativas. Estructuras mediastinales y grandes vasos sin alteraciones.
Correcto — IMPRESIÓN: Nódulo pulmonar sólido de 7 mm en lóbulo superior derecho estable respecto al control previo. Evaluación de nódulos milimétricos limitada por artefacto respiratorio en bases pulmonares.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B3-0063 · control_dimension (control) — RX de rodilla

Motivo: Trauma en rodilla; descartar fractura.

Correcto — INDICACIÓN: Mujer de 61 años con trauma en rodilla derecha, radiografía solicitada para descartar fractura.
Correcto — HALLAZGOS: Radiografía de rodilla en proyecciones anteroposterior y lateral. No se evidencian trazos de fractura ni luxación. Se identifica lesión lítica de bordes esclerosos en metáfisis proximal de la tibia que mide 32 x 25 x 20 mm, sin reacción perióstica agresiva. Cambios degenerativos femorotibiales moderados con osteofitos marginales y leve derrame articular.
Correcto — IMPRESIÓN: Lesión lítica de aspecto benigno en metáfisis tibial proximal de 32 mm, sin signos de fractura aguda. Gonartrosis moderada.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B3-0073 · control_menores (control) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: Mujer de 43 años para control de litiasis renal conocida.
Correcto — HALLAZGOS: Radiografía simple de abdomen en proyección anteroposterior con adecuada técnica y penetración. Se identifica imagen radiopaca de 6 mm proyectada sobre el polo inferior de la silueta renal derecha, compatible con litiasis conocida. No se observan nuevas imágenes radiopacas sugestivas de cálculo en el trayecto ureteral esperado ni en fosa renal izquierda, con patrón de gas intestinal dentro de límites normales. Cambios osteodegenerativos leves en columna lumbar como hallazgo incidental.
Correcto — IMPRESIÓN: Litiasis de 6 mm en polo inferior del riñón derecho sin cambios significativos respecto al antecedente referido. Sin evidencia de litiasis ureteral ni alteraciones agudas intestinales.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B3-0039 · omision (error) — RX de tórax

Motivo: Tos y fiebre de 5 días; descartar neumonía.

Correcto — INDICACIÓN: Hombre de 25 años con tos y fiebre de 5 días; descartar neumonía.
Correcto — HALLAZGOS: Los pulmones están bien inflados sin opacidades consolidativas ni atelectasias. Se identifica nódulo pulmonar sólido de 18 mm en el lóbulo superior derecho sin calcificaciones asociadas. No hay derrame pleural ni neumotórax. La silueta cardiomediastinal y las estructuras óseas son normales.
Correcto — IMPRESIÓN: No hay evidencia de neumonía. Nódulo pulmonar sólido de 18 mm en lóbulo superior derecho que requiere correlación con tomografía de tórax para caracterización.
Variante — INDICACIÓN: Hombre de 25 años con tos y fiebre de 5 días; descartar neumonía.
Variante — HALLAZGOS: Los pulmones están bien inflados sin opacidades consolidativas ni atelectasias. Se identifica nódulo pulmonar sólido de 18 mm en el lóbulo superior derecho sin calcificaciones asociadas. No hay derrame pleural ni neumotórax. La silueta cardiomediastinal y las estructuras óseas son normales.
Variante — IMPRESIÓN: No hay evidencia de neumonía. Estudio dentro de límites normales sin consolidaciones.
Esperado [omitted_finding/error]: body='Se identifica nódulo pulmonar sólido de 18 mm en el lóbulo superior derecho sin calcificaciones asociadas.' impresion='' (HALLAZGOS describe nódulo pulmonar de 18 mm que requiere estudio adicional y la IMPRESIÓN lo omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B3-0013 · doble_chequeo (verify) — RX de tórax

Motivo: Dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.

Correcto — INDICACIÓN: Mujer de 56 años con dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.
Correcto — HALLAZGOS: Radiografía de tórax en proyección posteroanterior con técnica inspiratoria adecuada. Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame pleural. No se evidencia neumotórax ni signos de tensión mediastinal. Silueta cardiomediastínica de tamaño y contorno normales. Estructuras óseas del tórax sin lesiones agudas.
Correcto — IMPRESIÓN: No se identifica neumotórax ni criterios de neumotórax a tensión. Radiografía de tórax sin alteraciones agudas.
Variante — INDICACIÓN: Mujer de 56 años con dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.
Variante — HALLAZGOS: Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame pleural. Silueta cardiomediastínica de tamaño y contorno normales. Sin neumotórax. Estructuras óseas del tórax sin lesiones agudas.
Variante — IMPRESIÓN: Radiografía de tórax sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar neumotórax a tensión' impresion='Radiografía de tórax sin alteraciones agudas.' (Estudio con indicación crítica de neumotórax a tensión informado con plantilla normal que requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B3-0046 · doble_chequeo (verify) — RX de abdomen

Motivo: Dolor abdominal súbito y defensa; descartar neumoperitoneo.

Correcto — INDICACIÓN: Dolor abdominal súbito y defensa; descartar neumoperitoneo.
Correcto — HALLAZGOS: Radiografía de abdomen simple en proyección anteroposterior con adecuada técnica y sin artefactos limitantes. Distribución normal del gas intestinal, sin dilatación de asas ni niveles hidroaéreos y sin evidencia de neumoperitoneo ni aire libre subdiafragmático. Siluetas renales y sombras de los psoas de aspecto usual, sin litiasis radiopaca evidente. Estructuras óseas sin lesiones agudas.
Correcto — IMPRESIÓN: No se identifica neumoperitoneo ni signos de perforación de víscera hueca. Radiografía de abdomen sin alteraciones agudas.
Variante — INDICACIÓN: Dolor abdominal súbito y defensa; descartar neumoperitoneo.
Variante — HALLAZGOS: Distribución normal del gas intestinal, sin niveles hidroaéreos ni neumoperitoneo. Siluetas renales y psoas de aspecto usual. Sin litiasis radiopaca evidente. Estructuras óseas sin lesiones agudas.
Variante — IMPRESIÓN: Radiografía de abdomen sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar neumoperitoneo' impresion='Radiografía de abdomen sin alteraciones agudas.' (Caso de doble chequeo donde el cuerpo responde pero la conclusión no nombra explícitamente el neumoperitoneo y la plantilla normal con motivo crítico requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B3-0051 · doble_chequeo (verify) — TC de cráneo simple

Motivo: Déficit neurológico súbito; descartar hemorragia intracraneal.

Correcto — INDICACIÓN: Hombre de 49 años con déficit neurológico súbito; descartar hemorragia intracraneal.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de hemorragia intraparenquimatosa, subaracnoidea ni colecciones extraaxiales. Sistema ventricular y espacios subaracnoideos de amplitud normal para la edad. Línea media centrada sin efecto de masa ni edema. Estructuras óseas sin trazos de fractura.
Correcto — IMPRESIÓN: TC de cráneo simple sin evidencia de hemorragia intracraneal ni otras alteraciones agudas.
Variante — INDICACIÓN: Hombre de 49 años con déficit neurológico súbito; descartar hemorragia intracraneal.
Variante — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Variante — IMPRESIÓN: TC de cráneo simple sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar hemorragia intracraneal' impresion='TC de cráneo simple sin alteraciones agudas.' (Estudio con indicación crítica informado con plantilla normal requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## B3-0005 · omision (error) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Mujer de 55 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Correcto — HALLAZGOS: Radiografía AP y lateral de rodilla derecha con adecuada técnica. Se observan cambios degenerativos tricompartimentales moderados con disminución del espacio articular femorotibial medial, esclerosis subcondral y osteofitos marginales. En la metáfisis proximal de la tibia se identifica lesión lítica de 32 mm de diámetro mayor, de bordes irregulares, sin esclerosis periférica. No se observa fractura aguda ni derrame articular significativo.
Correcto — IMPRESIÓN: Gonartrosis tricompartimental moderada. Lesión lítica de 32 mm en metáfisis proximal de la tibia de aspecto agresivo que requiere estudio complementario con RM y valoración por ortopedia oncológica.
Variante — INDICACIÓN: Mujer de 55 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Variante — HALLAZGOS: Radiografía AP y lateral de rodilla derecha con adecuada técnica. Se observan cambios degenerativos tricompartimentales moderados con disminución del espacio articular femorotibial medial, esclerosis subcondral y osteofitos marginales. En la metáfisis proximal de la tibia se identifica lesión lítica de 32 mm de diámetro mayor, de bordes irregulares, sin esclerosis periférica. No se observa fractura aguda ni derrame articular significativo.
Variante — IMPRESIÓN: Cambios degenerativos tricompartimentales moderados sin evidencia de fractura.
Esperado [omitted_finding/error]: body='En la metáfisis proximal de la tibia se identifica lesión lítica de 32 mm de diámetro mayor, de bordes irregulares, sin esclerosis periférica.' impresion='' (La impresión omite la lesión lítica de 32 mm descrita en hallazgos que requiere estudio adicional y cambia el manejo.)

- [ ] ✅ / ❌ — comentario:

## B3-0012 · control_limitacion (control) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Mujer de 22 años con dolor torácico y dímero D elevado para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del tronco y arterias pulmonares principales. No se observan defectos de llenado en arterias pulmonares centrales, lobares ni segmentarias. La evaluación de las ramas subsegmentarias es limitada por artefacto respiratorio. Parénquima pulmonar sin consolidaciones, sin derrame pleural y sin neumotórax; mediastino y grandes vasos sin alteraciones.
Correcto — IMPRESIÓN: No se identifica tromboembolismo pulmonar central, lobar ni segmentario; evaluación subsegmentaria limitada por artefacto respiratorio sin poder excluir completamente TEP distal.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B3-0072 · omision (error) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Mujer de 22 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Correcto — HALLAZGOS: Rodilla con adecuada alineación femorotibial sin disminución del espacio articular ni esclerosis subcondral. Se identifica lesión lítica excéntrica en metáfisis proximal de la tibia de 32 mm, de bordes irregulares con disrupción cortical y reacción perióstica en sol naciente. No se evidencia derrame articular significativo ni calcificaciones intraarticulares. Rótula de morfología y altura conservadas sin fracturas agudas.
Correcto — IMPRESIÓN: Lesión lítica agresiva de 32 mm en metáfisis proximal de la tibia sugestiva de neoplasia ósea primaria que requiere correlación con resonancia magnética y valoración por ortopedia oncológica. No se observan signos de gonartrosis ni otros cambios degenerativos.
Variante — INDICACIÓN: Mujer de 22 años con dolor crónico de rodilla para valoración de cambios degenerativos.
Variante — HALLAZGOS: Rodilla con adecuada alineación femorotibial sin disminución del espacio articular ni esclerosis subcondral. Se identifica lesión lítica excéntrica en metáfisis proximal de la tibia de 32 mm, de bordes irregulares con disrupción cortical y reacción perióstica en sol naciente. No se evidencia derrame articular significativo ni calcificaciones intraarticulares. Rótula de morfología y altura conservadas sin fracturas agudas.
Variante — IMPRESIÓN: No se observan signos de gonartrosis ni cambios degenerativos articulares. Rótula y alineación dentro de límites normales.
Esperado [omitted_finding/error]: body='Se identifica lesión lítica excéntrica en metáfisis proximal de la tibia de 32 mm, de bordes irregulares con disrupción cortical y reacción perióstica en sol naciente.' impresion='' (Los hallazgos describen lesión lítica agresiva de 32 mm que requiere estudio adicional y valoración especializada pero la impresión la omite por completo.)

- [ ] ✅ / ❌ — comentario:
