# Cómo generar tus 100 casos

No pidas los 100 de una sola vez. Un modelo de lenguaje, al pedirle volumen,
deja de leer la guía y empieza a rellenar con plantillas. Trabaja **por guía y
en tandas de 10**: adjunta una GPC, pide 10 casos, revísalos, y sigue con la
siguiente.

Con 10 guías tienes tus 100 casos, con la ventaja de que quedan repartidos en
10 temas distintos, que es justo lo que el muestreo estratificado necesita.

## Organizar por especialidad

El simulador deja que el alumno elija una especialidad antes de empezar, así
que conviene que el campo `especialidad` sea CONSISTENTE. Si en unos casos
escribes "Medicina Interna" y en otros "Med. Interna", el simulador los tomará
como dos especialidades distintas.

Usa exactamente uno de estos nombres, tal cual, en el campo `especialidad`:

- Medicina Interna
- Pediatría
- Ginecología y Obstetricia
- Cirugía General
- Medicina Familiar

Un flujo cómodo: dedica cada bloque de 10 guías a una especialidad. Bajas las
10 GPC de Medicina Interna, generas C001–C100 con `especialidad` fija en
"Medicina Interna", y ese archivo lo llamas `casos_medicina_interna.json`.
Repites con Pediatría en otro archivo. Puedes tener el banco de una sola
especialidad activo, o unir varios archivos en un `casos.json` con todo, y el
alumno elegirá desde el menú.

Dónde bajar las guías oficiales (el catálogo central del CENETEC está en
transición, pero el IMSS las mantiene): imss.gob.mx/guias_practicaclinica.
Descarga siempre las dos versiones, GER (completa) y GRR (rápida).

---

## Prompt (cópialo tal cual, adjuntando una guía cada vez)

```text
Adjunto la Guía de Práctica Clínica. Con base ÚNICAMENTE en su contenido,
redacta 10 casos clínicos tipo ENARM.

Devuelve un arreglo JSON válido y nada más: sin texto introductorio, sin
explicaciones y sin ``` alrededor.

REGLAS DE CONTENIDO
1. Cada viñeta debe traer datos clínicos concretos y verificables:
   edad exacta, sexo, antecedentes relevantes, tiempo de evolución, signos
   vitales con cifras, hallazgos de exploración física y resultados de
   laboratorio o gabinete con valores numéricos y unidades.
   Está PROHIBIDO usar frases como "sintomatología cardinal", "valores fuera
   de rango", "hallazgos compatibles con descompensación" o "según la sección
   correspondiente". Si no puedes poner una cifra real, no escribas el caso.
2. La respuesta correcta debe repartirse entre A, B, C y D a lo largo de los
   10 casos: aproximadamente la misma cantidad de cada letra. Nunca coloques
   la correcta siempre en la misma posición.
3. Las tres distractoras deben ser errores clínicos que un estudiante comete
   de verdad: el fármaco de segunda línea presentado como primera, un estudio
   innecesario, un diagnóstico diferencial plausible, una dosis o un plan
   equivocado. Nada absurdo ni descartable a simple vista.
4. En "guia_origen" cita el nombre y el número de la guía, más la sección o
   recomendación específica que sustenta la respuesta.
   En "especialidad" usa EXACTAMENTE uno de estos nombres, sin variaciones:
   Medicina Interna, Pediatría, Ginecología y Obstetricia, Cirugía General,
   Medicina Familiar.
5. En "retroalimentacion" explica por qué la correcta lo es Y por qué cada
   distractora no lo es. Mínimo tres renglones.
6. Marca "seriado" a 4 de los 10 casos (con 2 o 3 reactivos sobre la misma
   viñeta) y "unico" a los 6 restantes (con 1 reactivo).
7. Reparte los reactivos entre los cuatro niveles: diagnostico, tratamiento,
   prevencion, pronostico.

ESQUEMA EXACTO (respétalo campo por campo, sin agregar ni quitar propiedades)

[
  {
    "id": "C001",
    "especialidad": "Medicina Familiar",
    "tema": "nombre corto del padecimiento",
    "guia_origen": "nombre y número de la GPC, sección o recomendación",
    "tipo": "unico",
    "vineta": "caso clínico de 60 a 120 palabras con datos concretos",
    "reactivos": [
      {
        "enunciado": "pregunta del reactivo",
        "opciones": ["texto A", "texto B", "texto C", "texto D"],
        "respuesta_correcta": "B",
        "retroalimentacion": "por qué B es correcta y por qué A, C y D no",
        "nivel": "diagnostico"
      }
    ]
  }
]

Valores permitidos:
  "tipo":  unico | seriado
  "nivel": diagnostico | tratamiento | prevencion | pronostico
  "respuesta_correcta": A | B | C | D

Usa los IDs del C001 al C010 en esta tanda.
```

**Para la segunda tanda** cambia la última línea a `Usa los IDs del C011 al
C020`, y así sucesivamente hasta C100. Si repites IDs, el simulador te avisará
al cargar el banco.

---

## Cómo armar el archivo final

1. Guarda cada tanda en un archivo aparte: `tanda1.json`, `tanda2.json`, etc.
2. Une todo en un solo arreglo `casos.json`. Con un editor de texto basta:
   quita el `]` del final de un archivo y el `[` del inicio del siguiente,
   dejando una coma entre ellos.
3. Ejecuta la revisión:

```bash
python validar_banco.py casos.json
```

El script te dirá si hay errores de estructura, si la respuesta correcta está
cargada hacia una letra, y si alguna viñeta se ve como plantilla vacía.
Corrige lo que marque y vuelve a correrlo hasta que diga **sin alertas**.

---

## Lo que tienes que revisar tú, a mano

El validador detecta problemas de forma. La corrección clínica es tuya. Antes
de darlo a los alumnos, revisa en cada caso:

- ¿La respuesta marcada como correcta realmente lo es según la guía?
- ¿Alguna distractora también es defendible? Si dos opciones se sostienen, el
  reactivo está mal y hay que reescribirlo.
- ¿Las cifras de laboratorio son coherentes entre sí y con el cuadro clínico?
- ¿La retroalimentación enseña algo, o solo repite el enunciado?

Después de la primera aplicación, entra al panel docente, a la pestaña
**Reactivos**. Todo lo que tenga más de 80% de error casi siempre está mal
redactado, no es que el grupo no sepa.
