"""Consulta de certificados PSA.

La API pública de PSA (https://api.psacard.com/publicapi) sólo verifica
certificados: le pasas un número de cert y te devuelve qué carta es, la nota
y los datos de la etiqueta. El token se genera gratis desde tu cuenta de
psacard.com, pero el cupo del plan gratuito es muy corto (llegó a ser de
unas 100 llamadas al día y en 2026 se recortó drásticamente), así que la app
guarda en la base de datos lo que ya ha consultado y no vuelve a pedirlo.

No hay API oficial de informes de población en ninguna graduadora. Los
campos de POP se rellenan a mano desde psacard.com/pop y se quedan
guardados con la carta.
"""

import json
import urllib.error
import urllib.request

BASE = "https://api.psacard.com/publicapi"
POP_URL = "https://www.psacard.com/pop"


class PSAError(RuntimeError):
    pass


def cert_lookup(token, cert_number, timeout=15):
    if not token:
        raise PSAError("Falta el token de PSA en config.json")
    url = f"{BASE}/cert/GetByCertNumber/{str(cert_number).strip()}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "coleccion-tcg/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise PSAError("PSA ha cortado por límite de llamadas. Prueba mañana.") from exc
        raise PSAError(f"PSA respondió {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise PSAError(f"No hay conexión con PSA: {exc.reason}") from exc

    cert = data.get("PSACert") or {}
    if not cert or data.get("IsValidRequest") is False:
        raise PSAError(data.get("ServerMessage") or "Certificado no encontrado")

    return {
        "cert": cert.get("CertNumber"),
        "grade": cert.get("CardGrade"),
        "name": cert.get("Subject"),
        "year": cert.get("Year"),
        "brand": cert.get("Brand"),
        "number": cert.get("CardNumber"),
        "variety": cert.get("Variety"),
        "category": cert.get("Category"),
        "spec_id": cert.get("SpecID"),
        "pop_total": cert.get("TotalPopulation"),
        "pop_higher": cert.get("PopulationHigher"),
        "raw": cert,
    }
