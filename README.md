# collector.app — colección TCG

Inventario local de cartas (Pokémon, One Piece, fútbol, básquet, béisbol) con
precios de Cardmarket, historial propio y valor total de la colección.

Sólo usa la librería estándar de Python 3.9+. No hay que instalar nada, no
sube nada a ningún sitio y la base de datos es un fichero SQLite tuyo.

## Arrancar

```bash
python3 app.py
```

Abre `http://127.0.0.1:8765` en el navegador. Se queda escuchando sólo en tu
máquina.

Otros comandos:

```bash
python3 app.py sync              # importa los ficheros de data/
python3 app.py list              # la colección en el terminal
python3 app.py total             # sólo el valor total
python3 app.py export cartas.csv
python3 app.py importar copia.json     # copia hecha en collector.app
python3 app.py fotos                   # baja al disco la foto de cada carta
```

## Precios de Cardmarket

Cardmarket publica dos ficheros en <https://www.cardmarket.com/Data/Download>
(hay que estar logueado, son gratis para cualquier usuario):

- **guía de precios** de cada juego — se actualiza una vez al día
- **catálogo de productos** — se actualiza cuando sale una expansión

Descarga los de Pokémon y One Piece, déjalos en `data/` y pulsa **Sincronizar
precios** (o `python3 app.py sync`). El importador reconoce solo el formato
—CSV, JSON o comprimido en gzip— y los nombres de las columnas, porque
Cardmarket los ha ido cambiando.

Desde 2024 estos ficheros sustituyen al antiguo endpoint `/priceguide` de la
API, que quedó deprecado y luego retirado. Por eso la vía principal aquí son
los ficheros, no la API.

Después, en cada carta, usa **Buscar en el catálogo** para enlazarla con su
`idProduct`. A partir de ahí el precio se actualiza solo en cada
sincronización.

### Lo de las "últimas 5 ventas"

Cardmarket **no publica las ventas una a una** por ninguna vía, ni en la API
ni en los ficheros. Lo que sí publica es `AVG1`: el precio medio de las
unidades vendidas ese día. La app guarda un `AVG1` por carta y por día, así
que en cuanto sincronices unos días seguidos tendrás tu propio histórico de
ventas reales, que es lo que se dibuja en "Últimas medias diarias".

Sincroniza a diario y en cinco días tienes las cinco últimas. Si quieres que
sea automático, en Linux o Mac basta con un cron:

```
0 9 * * * cd /ruta/a/coleccion-tcg && /usr/bin/python3 app.py sync
```

Puedes valorar con `AVG7` (por defecto, el más estable), `Trend`, `AVG1`,
`AVG30` o el precio más bajo. Se cambia desde el selector de arriba.

## Cromos de fútbol, básquet y béisbol

**Cardmarket no vende cromos deportivos**, sólo juegos de cartas
coleccionables. Para Panini, Topps y compañía no hay ninguna fuente pública
gratuita de ventas cerradas: la API de eBay que da datos de vendidos
(Marketplace Insights) es de acceso restringido y hay que solicitarla.

Por eso, en esas tres categorías, las ventas se anotan a mano en la ficha de
cada carta (de eBay vendidos, 130point o subastas). La app hace el resto:
media, tendencia y total.

## Cartas graduadas

La guía de precios de Cardmarket es de cartas **sin graduar**. Un PSA 10 vale
bastante más, así que cada carta graduada tiene un **multiplicador de nota**:
si un PSA 10 se paga a 3× la carta suelta, pon 3. También puedes fijar un
**precio a mano**, que manda sobre todo lo demás.

Los datos de **POP** se rellenan a mano desde
<https://www.psacard.com/pop>. No existe API oficial de informes de población
en ninguna graduadora. La API pública de PSA sólo verifica certificados; si
tienes token, ponlo en `config.json` y la app puede consultarlo, pero el cupo
gratuito es muy corto.

## config.json (opcional)

Copia `config.example.json` a `config.json`:

```json
{
  "basis": "avg7",
  "port": 8765,
  "psa_token": "",
  "app_token": "", "app_secret": "",
  "access_token": "", "access_secret": ""
}
```

Las cuatro claves de Cardmarket son de una app creada en tu perfil de
Cardmarket (OAuth 1.0a). Sólo hacen falta para consultar ofertas vivas de una
carta; para los precios diarios no se necesitan.

## Fondos de cada sección

Cada pestaña tiene su propio escenario y su propio color de acento: Pokémon en
ámbar, One Piece en azul de mar, fútbol en verde de césped, básquet en naranja
de duela, béisbol en rojo de tierra batida.

**Pokémon se llena solo:**

```bash
python3 app.py art
```

Descarga la ilustración oficial de los Pokémon más conocidos desde PokéAPI,
que es pública, gratuita y no pide clave. Puedes pedir otros por nombre:
`python3 app.py art pokemon mewtwo gengar tyranitar`.

**Las demás las pones tú.** Deja las imágenes que quieras en su carpeta:

```
art/futbol/    art/basquet/    art/beisbol/    art/onepiece/
```

Sirven jpg, png y webp, y se cargan desde tu disco. No existe ninguna fuente
libre de fotos de futbolistas o de jugadores de la NBA y la MLB: son imágenes
con derechos de autor y derechos de imagen, así que no puedo empaquetarlas ni
descargarlas por ti. Escaneos de tus propias cartas funcionan muy bien y
además hacen la sección tuya.

Si una carpeta está vacía, la app dibuja un motivo propio en SVG —las líneas
del campo, el arco de triple, las costuras de la pelota, el oleaje— para que
la sección nunca se quede sin escenario.

## Buscador unificado

El buscador de la ficha de alta consulta tres sitios a la vez y los mezcla en
una sola lista:

- el **catálogo de Cardmarket** que tienes descargado (instantáneo, sin conexión)
- la **API de Cardmarket**, si has puesto credenciales en `config.json`
- **tus propias cartas**, para no duplicar nombres ni escribirlos distinto

Cada resultado dice de dónde sale y a cuánto está. Al elegir uno se rellenan
nombre, colección, número y rareza, y la carta queda atada a su `idProduct`.

Eso es lo que hace posible la comparación diaria: a partir de ese momento cada
actualización guarda una línea de precio para ese producto exacto, y la ficha
muestra la variación **frente a ayer, frente a hace 7 días y frente a hace 30**,
además del listado día a día. En la lista, cada carta enseña su movimiento del
día junto al precio.

Si además tienes credenciales, al pulsar Actualizar precios la app refresca por
API las cartas enlazadas, sin esperar al fichero diario.

## Colecciones grandes

Con mil cartas o más:

- La app del navegador guarda cartas, historial y fotos en la base de datos
  del navegador (IndexedDB), que admite cientos de megas. Mil cartas con foto
  ocupan unos 25 MB. El pie de página indica cuánto llevas.
- Si tu lista ya existe en una hoja de cálculo, guárdala como CSV y usa
  **Importar lista**. La **Plantilla CSV** enseña las columnas; reconoce
  nombres en español o en inglés en cualquier orden.
- Para pasar la colección del navegador a esta versión: descarga la copia
  `.json` desde la app y ejecuta `python3 app.py importar collector-app-FECHA.json`.
  Aquí no hay límite de espacio y `python3 app.py fotos` guarda las imágenes
  en disco.

## Estructura

```
app.py              arranque y comandos
tcg/db.py           SQLite: cartas, ventas, catálogo, historial de precios
tcg/cardmarket.py   importador de ficheros + cliente OAuth 1.0a
tcg/valuation.py    valor, tendencia y avisos (POP bajo, etc.)
tcg/server.py       servidor local y API JSON
tcg/psa.py          verificación de certificados
tcg/search.py       buscador unificado y variación diaria
tcg/art.py          fondos: PokéAPI, tus imágenes y motivos SVG
tcg/ui.py           la interfaz
art/                imágenes de fondo por sección
data/               aquí van los ficheros de Cardmarket
coleccion.db        tu colección
```


## Compartir la colección (móvil, otro ordenador, dos personas a la vez)

1. En el Mac que hará de servidor, doble clic en **«Compartir en la wifi.command»**
   (o en el terminal: `python3 app.py serve`).
2. El terminal enseña dos direcciones. La segunda, del estilo
   `http://192.168.1.34:8765/`, es la que se escribe en el navegador del móvil
   o del otro ordenador (misma wifi).
3. Listo: todos ven y editan **la misma base de datos**. Cada pocos segundos la
   app recoge lo que hayan añadido los demás, y si dos personas guardan a la vez
   se mezcla carta a carta ganando la edición más reciente. Los borrados también
   se propagan.

Notas:
- La base compartida vive en `coleccion.db`, junto a este archivo. Haz copias
  de vez en cuando con el botón «Descargar copia».
- Las **fotos guardadas** siguen siendo locales de cada aparato (pesan mucho);
  las imágenes normales de las cartas se ven igual en todos.
- Sólo funciona dentro de tu wifi: nada sale a internet. Para usarlo tú solo
  sin compartir: `python3 app.py serve --solo`.

## Paquetes de cartas (compartir a distancia, sin wifi común)

En la app: filtra lo que quieras regalar o enseñar (una pestaña, una búsqueda)
y pulsa **«Compartir paquete»**: se descarga un fichero con esas cartas y sus
fotos. Envíalo por WhatsApp, correo o como sea. La otra persona pulsa
**«Sumar paquete»**, elige el fichero, y esas cartas se añaden a su colección;
las que ya tuviera (mismo nombre, número, colección y variante) se saltan solas.

## Web pública con cuentas (cada persona su colección)

Arranca con `python3 app.py serve --cuentas`. Al abrir la app pedirá crear
cuenta o entrar (nombre + clave de 6+); cada usuario guarda y sincroniza su
propia colección, aislada de las demás. El botón «Salir (nombre)» cierra la
sesión. Sin `--cuentas` todo sigue como siempre: base compartida en la wifi.

Para subirlo a internet (Railway, Render, PythonAnywhere): despliega esta
carpeta, comando de arranque `python3 app.py serve --cuentas --port $PORT`,
y el hosting pone el HTTPS. Desde el móvil, «Añadir a pantalla de inicio»
instala la app con su icono (PWA).
