# Activar los avisos push (Render)

Añade estas **dos variables nuevas** en Render → tu servicio →
Environment → Edit → Add variable:

**VAPID_PUBLIC_KEY** (no es secreta, se puede ver):
```
BObOQ2oDI1sS27iqF1LJv1qbdbZerxJrSNcoBID8f81AbocuHtkA91BS1zeSrF2VlCLf9dZqX6jZY3E9mw0bV0U
```

**VAPID_PRIVATE_KEY** (secreta — pégala tal cual, con los saltos de línea):
```
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgEiOGDehU6drkl4l6
hAcp0ZZ5Lwb4+x0bP7lPgNxNAR+hRANCAATmzkNqAyNbEtu4qhdSyb9am3W2Xq8S
a0jXKASA/H/NQG6HLh7ZAPdQUtc3kqxdlZQi3/XWal+o2WNxPZsNG1dF
-----END PRIVATE KEY-----
```

(Opcional) **VAPID_CONTACT**: un correo de contacto que Apple/Google pueden
usar si algo va mal con tus avisos push. Si no lo pones, se usa
`aviso@collector.app` por defecto.

Guarda con **Save, rebuild, and deploy**. Al desplegar, Render instalará
`pywebpush` solo (ya está en `requirements.txt`).

## Cómo probarlo

1. En tu web, entra con una cuenta → círculo de usuario → **🔔 Avisos en el
   móvil** → el navegador pedirá permiso de notificaciones → acéptalo.
2. Marca una carta de tu lista de deseos con un objetivo ya alcanzado (o
   pide a alguien que lo haga) para que el cazador dispare un aviso — o,
   más simple, dímelo cuando esté desplegado y hago la prueba desde el
   navegador.
3. Deberías recibir la notificación aunque tengas la pestaña cerrada.

Estas claves son solo para collector.app — no las compartas ni las subas a
ningún sitio público (como un repositorio en abierto).
