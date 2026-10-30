# Bloque 500 train v5 — muestra de revisión (10 casos al azar, semilla 47, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## B5-0053 · control_pregunta_cuerpo (control) — RX de tórax

Motivo: Disnea; descartar derrame pleural.

Correcto — INDICACIÓN: Hombre de 26 años con disnea, se solicita descartar derrame pleural.
Correcto — HALLAZGOS: Radiografía de tórax en proyecciones posteroanterior y lateral con adecuada técnica e inspiración. No se evidencia derrame pleural ni neumotórax. Parénquima pulmonar sin consolidaciones ni opacidades focales, silueta cardiomediastinal de tamaño y contornos conservados. Estructuras óseas y tejidos blandos sin alteraciones.
Correcto — IMPRESIÓN: Estudio dentro de límites normales. No se observan consolidaciones ni alteraciones cardiomediastinales.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B5-0011 · omision (error) — RX de rodilla

Motivo: Derrame articular; descartar lesión ósea.

Correcto — INDICACIÓN: Mujer de 66 años con derrame articular de rodilla, para descartar lesión ósea.
Correcto — HALLAZGOS: Radiografía de rodilla en proyecciones anteroposterior y lateral. Se observa derrame articular moderado con distensión de la bursa suprapatelar. Lesión lítica de aspecto agresivo de 34 mm en la metáfisis distal del fémur, con bordes mal definidos, reacción perióstica lamelar y ruptura cortical focal. Cambios degenerativos femorotibiales moderados con osteofitos marginales y estrechamiento del compartimento medial. No se identifica fractura aguda desplazada.
Correcto — IMPRESIÓN: Derrame articular moderado. Lesión lítica agresiva de 34 mm en metáfisis distal del fémur, sugestiva de lesión neoplásica; se recomienda correlación con RM y valoración por ortopedia oncológica. Gonartrosis moderada tricompartimental.
Variante — INDICACIÓN: Mujer de 66 años con derrame articular de rodilla, para descartar lesión ósea.
Variante — HALLAZGOS: Radiografía de rodilla en proyecciones anteroposterior y lateral. Se observa derrame articular moderado con distensión de la bursa suprapatelar. Lesión lítica de aspecto agresivo de 34 mm en la metáfisis distal del fémur, con bordes mal definidos, reacción perióstica lamelar y ruptura cortical focal. Cambios degenerativos femorotibiales moderados con osteofitos marginales y estrechamiento del compartimento medial. No se identifica fractura aguda desplazada.
Variante — IMPRESIÓN: Derrame articular moderado. Gonartrosis moderada tricompartimental sin fractura aguda evidente.
Esperado [omitted_finding/error]: body='Lesión lítica de aspecto agresivo de 34 mm en la metáfisis distal del fémur, con bordes mal definidos, reacción perióstica lamelar y ruptura cortical focal.' impresion='' (HALLAZGOS describe lesión lítica agresiva de 34 mm que cambia el manejo y requiere estudio adicional, pero la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B5-0063 · pregunta (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en hipocondrio derecho; descartar colecistitis.

Correcto — INDICACIÓN: Mujer de 75 años con dolor en hipocondrio derecho para descartar colecistitis.
Correcto — HALLAZGOS: Hígado de tamaño y morfología conservados, con lesión hipodensa compatible con quiste simple de 14 mm en segmento VI, sin lesiones focales sólidas. Vesícula biliar distendida de paredes finas (2 mm), sin cálculos hiperdensos, sin líquido perivesicular ni realce parietal patológico, sin dilatación de la vía biliar intra ni extrahepática. Páncreas, bazo y glándulas suprarrenales sin alteraciones. Riñones de contornos regulares, sin hidronefrosis ni cálculos obstructivos; se identifica quiste cortical de 12 mm en riñón izquierdo. No se observan colecciones, neumoperitoneo ni adenopatías significativas; apéndice cecal de calibre normal y asas intestinales sin signos de obstrucción.
Correcto — IMPRESIÓN: Quistes hepático y renal simples, sin hallazgos de significación aguda. No se observan signos tomográficos de colecistitis aguda ni dilatación biliar.
Variante — INDICACIÓN: Mujer de 75 años con dolor en hipocondrio derecho para descartar colecistitis.
Variante — HALLAZGOS: Hígado de tamaño y morfología conservados, con lesión hipodensa compatible con quiste simple de 14 mm en segmento VI, sin lesiones focales sólidas. Páncreas, bazo y glándulas suprarrenales sin alteraciones. Riñones de contornos regulares, sin hidronefrosis ni cálculos obstructivos; se identifica quiste cortical de 12 mm en riñón izquierdo. No se observan colecciones, neumoperitoneo ni adenopatías significativas; apéndice cecal de calibre normal y asas intestinales sin signos de obstrucción.
Variante — IMPRESIÓN: Quistes hepático y renal simples, sin hallazgos de significación aguda. No se observan colecciones ni adenopatías significativas.
Esperado [indication_unanswered/error]: body='descartar colecistitis' impresion='No se observan colecciones ni adenopatías significativas.' (La indicación pide descartar colecistitis y ni hallazgos ni impresión responden la pregunta.)

- [ ] ✅ / ❌ — comentario:

## B5-0080 · omision (error) — TC de abdomen y pelvis con contraste

Motivo: Dolor en hipocondrio derecho; descartar colecistitis.

Correcto — INDICACIÓN: TC de abdomen y pelvis con contraste en mujer de 36 años con dolor en hipocondrio derecho para descartar colecistitis.
Correcto — HALLAZGOS: Vesícula biliar de paredes delgadas sin litiasis ni signos inflamatorios perivesiculares. Hígado, páncreas, bazo y suprarrenales sin alteraciones, sin dilatación de la vía biliar. Se identifica lesión sólida hipodensa de 32 mm en el polo inferior del riñón derecho, de bordes bien definidos y realce heterogéneo postcontraste. No hay adenopatías, líquido libre ni alteraciones agudas en apéndice y anexos.
Correcto — IMPRESIÓN: Vesícula biliar sin signos de colecistitis aguda. Lesión sólida de 32 mm en riñón derecho que requiere caracterización adicional y valoración por urología.
Variante — INDICACIÓN: TC de abdomen y pelvis con contraste en mujer de 36 años con dolor en hipocondrio derecho para descartar colecistitis.
Variante — HALLAZGOS: Vesícula biliar de paredes delgadas sin litiasis ni signos inflamatorios perivesiculares. Hígado, páncreas, bazo y suprarrenales sin alteraciones, sin dilatación de la vía biliar. Se identifica lesión sólida hipodensa de 32 mm en el polo inferior del riñón derecho, de bordes bien definidos y realce heterogéneo postcontraste. No hay adenopatías, líquido libre ni alteraciones agudas en apéndice y anexos.
Variante — IMPRESIÓN: Vesícula biliar sin signos de colecistitis aguda. Estudio sin otros hallazgos agudos.
Esperado [omitted_finding/error]: body='Se identifica lesión sólida hipodensa de 32 mm en el polo inferior del riñón derecho, de bordes bien definidos y realce heterogéneo postcontraste.' impresion='' (Los hallazgos describen una lesión renal sólida de 32 mm que requiere estudio adicional y cambia el manejo, pero la impresión la omite.)

- [ ] ✅ / ❌ — comentario:

## B5-0066 · omision (error) — RX de tórax

Motivo: Disnea; descartar derrame pleural.

Correcto — INDICACIÓN: Mujer de 66 años con disnea, radiografía de tórax solicitada para descartar derrame pleural.
Correcto — HALLAZGOS: Radiografía de tórax en proyecciones posteroanterior y lateral con adecuada técnica e inspiración. No se observa derrame pleural ni engrosamiento pleural, con ángulos costofrénicos libres. Se identifica nódulo pulmonar sólido de 23 mm en lóbulo superior derecho, de bordes espiculados. Silueta cardíaca de tamaño normal, mediastino centrado sin ensanchamiento. Estructuras óseas sin lesiones agudas evidentes.
Correcto — IMPRESIÓN: No hay signos de derrame pleural. Nódulo pulmonar sólido de 23 mm en lóbulo superior derecho, de bordes espiculados, requiere correlación con tomografía de tórax para caracterización.
Variante — INDICACIÓN: Mujer de 66 años con disnea, radiografía de tórax solicitada para descartar derrame pleural.
Variante — HALLAZGOS: Radiografía de tórax en proyecciones posteroanterior y lateral con adecuada técnica e inspiración. No se observa derrame pleural ni engrosamiento pleural, con ángulos costofrénicos libres. Se identifica nódulo pulmonar sólido de 23 mm en lóbulo superior derecho, de bordes espiculados. Silueta cardíaca de tamaño normal, mediastino centrado sin ensanchamiento. Estructuras óseas sin lesiones agudas evidentes.
Variante — IMPRESIÓN: No hay signos de derrame pleural. Silueta cardíaca y estructuras óseas sin alteraciones agudas.
Esperado [omitted_finding/error]: body='Se identifica nódulo pulmonar sólido de 23 mm en lóbulo superior derecho, de bordes espiculados.' impresion='' (Hallazgo clínicamente significativo que cambia manejo (nódulo de 23 mm que requiere seguimiento) descrito en hallazgos y omitido en la impresión.)

- [ ] ✅ / ❌ — comentario:

## B5-0084 · doble_chequeo (verify) — TC de cráneo simple

Motivo: Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.

Correcto — INDICACIÓN: Mujer de 82 años con Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.
Correcto — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Correcto — IMPRESIÓN: TC de cráneo simple sin hematoma ni hemorragia intracraneal aguda.
Variante — INDICACIÓN: Mujer de 82 años con Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.
Variante — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Variante — IMPRESIÓN: TC de cráneo simple sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar hematoma' impresion='TC de cráneo simple sin alteraciones agudas.' (La indicación pide descartar hematoma, el cuerpo responde pero la conclusión no nombra la patología.)

- [ ] ✅ / ❌ — comentario:

## B5-0051 · omision (error) — TC de tórax

Motivo: Estadificación de neoplasia conocida.

Correcto — INDICACIÓN: Mujer de 25 años, TC de tórax con contraste para estadificación de neoplasia conocida.
Correcto — HALLAZGOS: Parénquima pulmonar sin nódulos ni consolidaciones y sin derrame pleural. Se identifica adenopatía mediastinal en estación 7 de 18 mm de eje corto, heterogénea y de bordes irregulares, sugestiva de compromiso neoplásico. Hígado visualizado en cortes superiores sin lesiones focales. Corazón y grandes vasos de calibre y morfología conservados. Estructuras óseas incluidas sin lesiones líticas ni blásticas.
Correcto — IMPRESIÓN: Adenopatía mediastinal en estación 7 de 18 mm sugestiva de metástasis, requiere correlación oncológica y estudios adicionales. No se observan lesiones metastásicas pulmonares.
Variante — INDICACIÓN: Mujer de 25 años, TC de tórax con contraste para estadificación de neoplasia conocida.
Variante — HALLAZGOS: Parénquima pulmonar sin nódulos ni consolidaciones y sin derrame pleural. Se identifica adenopatía mediastinal en estación 7 de 18 mm de eje corto, heterogénea y de bordes irregulares, sugestiva de compromiso neoplásico. Hígado visualizado en cortes superiores sin lesiones focales. Corazón y grandes vasos de calibre y morfología conservados. Estructuras óseas incluidas sin lesiones líticas ni blásticas.
Variante — IMPRESIÓN: Parénquima pulmonar sin lesiones metastásicas ni consolidaciones. No se observa derrame pleural.
Esperado [omitted_finding/error]: body='Se identifica adenopatía mediastinal en estación 7 de 18 mm de eje corto, heterogénea y de bordes irregulares, sugestiva de compromiso neoplásico.' impresion='' (HALLAZGOS describe adenopatía mediastinal de 18 mm sugestiva de metástasis que cambia el manejo y requiere estudio adicional, pero la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## B5-0037 · control_parafrasis (control) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 24 años con dolor torácico y dímero D elevado para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con medio de contraste intravenoso sin defectos de llenado en el tronco pulmonar, arterias pulmonares principales, lobares, segmentarias y subsegmentarias. Tronco de la arteria pulmonar mide 24 mm de diámetro. No hay signos de sobrecarga cardiaca derecha, consolidaciones, derrame pleural ni neumotórax. Estructuras mediastinales y grandes vasos de calibre y trayecto conservados.
Correcto — IMPRESIÓN: Estudio sin evidencia de tromboembolismo pulmonar agudo. Tronco pulmonar de 24 mm sin signos de hipertensión pulmonar ni otros hallazgos agudos intratorácicos.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## B5-0074 · omision (error) — TC de cráneo simple

Motivo: Cefalea crónica de reciente cambio de patrón.

Correcto — INDICACIÓN: Mujer de 56 años con cefalea crónica de reciente cambio de patrón remitida para TC simple de cráneo.
Correcto — HALLAZGOS: TC simple de cráneo sin evidencia de hemorragia intra o extraaxial ni colecciones hemáticas. Parénquima encefálico de densidad conservada, sin hipodensidades sugestivas de isquemia aguda, con sistema ventricular y espacios subaracnoideos de amplitud normal y línea media centrada. Se identifica lesión extraaxial hiperdensa de 22 mm en la convexidad frontal derecha, de base dural ancha, sugestiva de meningioma, sin edema vasogénico asociado significativo. Neumatización conservada de senos paranasales y celdillas mastoideas, sin ocupación ni niveles; calota sin lesiones líticas ni trazos de fractura.
Correcto — IMPRESIÓN: Lesión extraaxial frontal derecha de 22 mm de base dural sugestiva de meningioma, se sugiere valoración por resonancia magnética contrastada para caracterización y seguimiento por neurocirugía. No se observa hemorragia intracraneal ni signos de isquemia aguda.
Variante — INDICACIÓN: Mujer de 56 años con cefalea crónica de reciente cambio de patrón remitida para TC simple de cráneo.
Variante — HALLAZGOS: TC simple de cráneo sin evidencia de hemorragia intra o extraaxial ni colecciones hemáticas. Parénquima encefálico de densidad conservada, sin hipodensidades sugestivas de isquemia aguda, con sistema ventricular y espacios subaracnoideos de amplitud normal y línea media centrada. Se identifica lesión extraaxial hiperdensa de 22 mm en la convexidad frontal derecha, de base dural ancha, sugestiva de meningioma, sin edema vasogénico asociado significativo. Neumatización conservada de senos paranasales y celdillas mastoideas, sin ocupación ni niveles; calota sin lesiones líticas ni trazos de fractura.
Variante — IMPRESIÓN: TC simple de cráneo sin evidencia de hemorragia intracraneal ni signos de isquemia aguda. Sistema ventricular y línea media de aspecto normal, sin efecto de masa.
Esperado [omitted_finding/error]: body='Se identifica lesión extraaxial hiperdensa de 22 mm en la convexidad frontal derecha, de base dural ancha, sugestiva de meningioma, sin edema vasogénico asociado significativo.' impresion='' (Hallazgos describe lesión extraaxial de 22 mm sugestiva de meningioma que requiere estudio adicional y seguimiento, pero la impresión no la menciona.)

- [ ] ✅ / ❌ — comentario:

## B5-0057 · omision (error) — RX de tórax

Motivo: Control de catéter venoso central.

Correcto — INDICACIÓN: Control de catéter venoso central en mujer de 86 años.
Correcto — HALLAZGOS: Catéter venoso central de acceso yugular derecho con extremo distal proyectado sobre la vena cava superior distal, sin evidencia de acodadura. Parénquima pulmonar sin opacidades alveolares, sin derrame pleural ni neumotórax visible. Se identifica opacidad nodular de 22 mm en el lóbulo superior derecho, de bordes espiculados, sugestiva de lesión de novo. Silueta cardiaca y mediastino de tamaño y contornos conservados. Estructuras óseas sin fracturas ni lesiones líticas evidentes.
Correcto — IMPRESIÓN: Catéter venoso central derecho normoposicionado sin complicaciones inmediatas. Opacidad nodular espiculada de 22 mm en lóbulo superior derecho, altamente sugestiva de neoplasia; se recomienda complementar con TC de tórax contrastada.
Variante — INDICACIÓN: Control de catéter venoso central en mujer de 86 años.
Variante — HALLAZGOS: Catéter venoso central de acceso yugular derecho con extremo distal proyectado sobre la vena cava superior distal, sin evidencia de acodadura. Parénquima pulmonar sin opacidades alveolares, sin derrame pleural ni neumotórax visible. Se identifica opacidad nodular de 22 mm en el lóbulo superior derecho, de bordes espiculados, sugestiva de lesión de novo. Silueta cardiaca y mediastino de tamaño y contornos conservados. Estructuras óseas sin fracturas ni lesiones líticas evidentes.
Variante — IMPRESIÓN: Catéter venoso central derecho normoposicionado sin complicaciones inmediatas. Parénquima pulmonar y silueta cardiomediastinal sin alteraciones agudas.
Esperado [omitted_finding/error]: body='Se identifica opacidad nodular de 22 mm en el lóbulo superior derecho, de bordes espiculados, sugestiva de lesión de novo.' impresion='' (HALLAZGOS describe nódulo pulmonar de 22 mm que requiere estudio adicional y la IMPRESIÓN lo omite por completo.)

- [ ] ✅ / ❌ — comentario:
