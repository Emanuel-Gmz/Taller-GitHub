# Bongo Cat de escritorio (sin OBS)

Gatito flotante siempre-arriba que reacciona a teclado y mouse a nivel
de todo el sistema (no hace falta que su ventana tenga el foco).

## Instalar y correr

```
pip install -r requirements.txt
python main.py
```

En Windows, si el hook global de teclado/mouse no reacciona, probá
correr la consola como administrador la primera vez.

## Controles

- **Click izquierdo + arrastrar**: mover el gatito.
- **Rueda del mouse**: agrandar / achicar.
- **Click derecho sobre el gato**: menú (Colección, sonido, click-through, salir).
- **F9**: alterna "click-through" en cualquier momento (util si activaste
  click-through y ya no podés hacer click derecho sobre el gato).
- Icono en la **bandeja del sistema**: mismo menú, siempre accesible
  aunque el click-through esté activado.

## Funciones incluidas

- **Sonido de tecla**: `assets/sounds/key.wav`. Se corta solo a los 2
  segundos y nunca se superpone (si llega una tecla nueva mientras
  suena, corta el sonido anterior y arranca de nuevo). Por default trae
  uno de los sonidos que ya venían en el plugin original (modo
  "feixue"). Para poner el tuyo: reemplazá ese archivo por cualquier
  `.wav` (podés convertir mp3→wav con `ffmpeg -i tuaudio.mp3 assets/sounds/key.wav`).
- **Reacción distinta por botón**: click izquierdo → pata izquierda,
  click derecho → pata derecha + carita sorprendida, scroll → carita
  de "dame plata" (gag que ya venía en el pack original).
- **Combo de tipeo rápido**: si escribís 6+ teclas en menos de 1
  segundo, el gato pone cara de esfuerzo (sonrojado) mientras dura el
  combo.
- **Ctrl+C / Ctrl+V**: animación especial (lentes "cool" al copiar,
  cara sorprendida al pegar).
- **Colección de gatitos**: menú aparte (click derecho → "Colección de
  gatitos...", o desde la bandeja) que muestra los 5 gatitos del plugin
  original y cuáles están desbloqueados según las teclas totales que
  tipeaste:
  - Clásico (2 manos): desbloqueado desde el inicio
  - Mania: 300 teclas
  - Standard: 1500 teclas
  - Feixue: 3000 teclas
  - Bilibili Duo: 6000 teclas
  
  **Importante**: Standard, Feixue y Bilibili Duo en el plugin
  original dibujan la pata derecha con un modelo 3D Live2D (Cubism
  SDK) — esta versión standalone no incluye ese motor, así que esos 3
  quedan visibles en la Colección (para que sepas que existen y cuánto
  falta) pero marcados como "no disponibles", en vez de mostrarte un
  gatito roto o a medias. Si me pasás sprites PNG propios para esos 3
  modos (como los de Clásico/Mania), los agrego sin problema.
- **Config persistente**: posición, tamaño, gatito elegido, sonido
  on/off, click-through, y estadísticas se guardan solos en
  `config.json` (se crea al lado de `main.py`) y se recuperan la
  próxima vez que abrís la app.
- **Click-through**: si lo activás, los clicks le pasan de largo al
  gato (no bloquea lo que hay debajo), pero el gato sigue reaccionando
  igual porque el hook de teclado/mouse es global, no depende del
  foco de su ventana.
- **Estadísticas**: pasá el mouse por arriba del gato para ver un
  tooltip con "teclas hoy" y "teclas en total" (el contador de hoy se
  reinicia solo cuando cambia el día).
- **Modo ronroneo**: si pasan 90 segundos sin ninguna tecla ni click,
  el gato empieza a bambolearse suave (efecto "respirando"). Si más
  adelante me pasás un audio de ronroneo, lo agrego para que también
  suene en loop mientras dura este modo.

## Estructura

```
main.py              -> ventana principal, hooks globales, menús
assets_manager.py     -> carga y compone los sprites por modo
sound_manager.py      -> sonido de tecla (corte a 2s, sin superposición)
config.py             -> guardar/cargar config.json
collection_dialog.py  -> ventana de "Colección de gatitos"
assets/
  modes/keyboard/      -> gatito clásico (2 manos, PNG puro)
  modes/mania/          -> gatito mania (2 manos, PNG puro)
  faces/0-3.png          -> las 4 caras reciclonas del plugin original
  sounds/key.wav          -> sonido de tecla por defecto
```
