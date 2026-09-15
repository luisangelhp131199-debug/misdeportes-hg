import asyncio
import json
import base64
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

def limpiar_texto(texto):
    texto = re.sub(r"[▶▼▲◄►•]", "", texto)
    return " ".join(texto.split()).strip()

def decodificar_stream(url_watch):
    """Extrae y decodifica el parámetro stream de Rústico TV para obtener la URL interna limpia"""
    try:
        if "stream=" in url_watch:
            match = re.search(r"stream=([^&]+)", url_watch)
            if match:
                encoded_str = match.group(1)
                # Padding seguro para base64
                padded = encoded_str + "=" * (-len(encoded_str) % 4)
                decoded_bytes = base64.b64decode(padded)
                return decoded_bytes.decode("utf-8")
    except Exception:
        pass
    return url_watch

async def obtener_agenda():
    url = "https://rusticotv.quest/"
    print(f"Iniciando extracción desde {url}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=40000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error al cargar la página: {e}")
            await browser.close()
            return

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        agenda_data = []

        contenedor_agenda = soup.find(id="fa-agenda-wrap") or soup.find(class_=re.compile("agenda", re.I))
        contenedores = contenedor_agenda.find_all(["div", "tr", "li"]) if contenedor_agenda else soup.find_all(["div", "tr", "li"], class_=re.compile("match|evento|partido|row", re.I))

        print(f"🔍 Procesando {len(contenedores)} bloques...")

        for cont in contenedores:
            enlaces = cont.find_all("a", href=True)
            if not enlaces:
                continue

            canales = []
            for a in enlaces:
                href = a["href"]
                texto_canal = limpiar_texto(a.text)

                if len(texto_canal) > 1 and not any(x in href.lower() for x in ["telegram", "whatsapp", "facebook", "twitter", "javascript", "#", "instagram"]):
                    if href.startswith("/"):
                        link_completo = f"https://rusticotv.quest{href}"
                    elif href.startswith("http"):
                        link_completo = href
                    else:
                        continue
                    
                    # Obtenemos la URL real limpia por debajo
                    url_limpia = decodificar_stream(link_completo)

                    canales.append({
                        "canal": texto_canal,
                        "url_real": url_limpia
                    })

            if canales:
                cont_copy = BeautifulSoup(str(cont), "html.parser")
                for a_tag in cont_copy.find_all("a"):
                    a_tag.decompose()

                nombre_evento = limpiar_texto(cont_copy.get_text())

                if len(nombre_evento) > 3:
                    if not any(e["evento"] == nombre_evento for e in agenda_data):
                        agenda_data.append({
                            "evento": nombre_evento,
                            "opciones": canales
                        })

        await browser.close()

        with open("agenda.json", "w", encoding="utf-8") as f:
            json.dump(agenda_data, f, ensure_ascii=False, indent=4)

        print(f"✅ ¡Listo! Se guardaron {len(agenda_data)} eventos en 'agenda.json'.")

if __name__ == "__main__":
    asyncio.run(obtener_agenda())
