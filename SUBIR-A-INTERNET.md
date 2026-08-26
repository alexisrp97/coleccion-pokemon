# Subir collector.app a internet (30 minutos, todo con clics)

## 1. Sube la carpeta a GitHub (el almacén del código)
1. Entra en github.com → Sign up (cuenta gratis).
2. Botón «+» arriba a la derecha → **New repository** → nombre `collector-app` → Create.
3. En la página del repositorio: enlace «uploading an existing file».
4. Arrastra TODO el contenido de esta carpeta (tcg.py, la carpeta tcg,
   collector.app.html, Procfile, requirements.txt, icon.png, README...)
   → botón verde **Commit changes**.

## 2. Enciende el servidor en Render (el ordenador en la nube)
1. Entra en render.com → Get Started → «Sign in with GitHub».
2. **New → Web Service** → elige tu repositorio `collector-app`.
3. Rellena:
   - Language: **Python 3**
   - Build command: (déjalo como está)
   - Start command: `python3 tcg.py serve --cuentas --port $PORT`
   - Instance type: **Free**
4. **Deploy Web Service** y espera 2-3 minutos.
5. Arriba aparece tu dirección: `https://collector-app-XXXX.onrender.com` ← tu web.

## 3. Estrénala
1. Abre esa dirección: te pedirá crear cuenta (nombre + clave de 6+).
2. Para cargar tu colección: en tu Mac, abre tu collector.app de siempre
   → «Descargar copia». Luego, en la web, arrastra ese fichero encima. Listo.
3. En el móvil: abre la dirección → menú del navegador →
   «Añadir a pantalla de inicio» → icono propio, como una app.

## Cosas que debes saber (sin letra pequeña)
- El plan Free de Render se duerme tras 15 min sin visitas: la primera
  entrada del día tarda ~1 minuto en despertar. Normal.
- En el plan Free, el disco del servidor se vacía cuando Render redespliega.
  No es drama: la colección de cada usuario vive TAMBIÉN en su navegador y
  se vuelve a subir sola al entrar; y la app descarga copias semanales.
  Si algún día quieres disco permanente: Railway (~5 $/mes) con «Volume».
- Cada cambio futuro: subes el archivo nuevo a GitHub (mismo arrastre)
  y Render redespliega solo.
