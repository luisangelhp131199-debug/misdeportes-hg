import json
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

def limpiar_texto(texto):
    texto = re.sub(r"[▶▼▲◄►•]", "", texto)
    return " ".join(texto.split()).strip()

async def obtener_agenda():
    url = "https://rusticotv.la/"
    print("Iniciando extracción de agenda desde Rustico TV...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error al cargar la página: {e}")
            await browser.close()
            return

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        agenda_data = []

        # Buscamos los bloques de eventos o partidos en Rustico TV
        # (Suelen agruparse en tarjetas, contenedores de partidos o filas de tablas)
        contenedores = soup.find_all(["div", "tr", "li"], class_=re.compile("evento|match|partido|game|row", re.I))
        
        if not contenedores:
            # Plan B: Si la estructura cambia, buscamos cualquier lista o bloque con enlaces de canales
            contenedores = soup.find_all("div", class_=re.compile("col|card|box", re.I))

        for cont in contenedores:
            enlaces = cont.find_all("a", href=True)
            if not enlaces:
                continue

            canales = []
            for a in enlaces:
                href = a["href"]
                texto_canal = limpiar_texto(a.text)

                # Filtramos para asegurarnos de que sean enlaces de canales/reproductores y no publicidad
                if len(texto_canal) > 1 and not any(x in href.lower() for x in ["telegram", "whatsapp", "facebook", "twitter", "javascript", "#"]):
                    link_completo = f"https://rusticotv.la{href}" if href.startswith("/") else href
                    
                    canales.append({
                        "canal": texto_canal,
                        "url_embed": link_completo,
                        "url_real": link_completo # Rustico carga directo los embeds limpios
                    })

            if canales:
                # Extraemos el texto del evento eliminando los botones de canales
                cont_copy = BeautifulSoup(str(cont), "html.parser")
                for a_tag in cont_copy.find_all("a"):
                    a_tag.decompose()

                nombre_evento = limpiar_texto(cont_copy.get_text())

                # Si encontramos un nombre válido y canales asociados, lo guardamos
                if len(nombre_evento) > 3:
                    # Evitamos duplicados exactos
                    if not any(e["evento"] == nombre_evento for e in agenda_data):
                        agenda_data.append({
                            "evento": nombre_evento,
                            "opciones": canales
                        })

        await browser.close()

        with open("agenda.json", "w", encoding="utf-8") as f:
            json.dump(agenda_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Se guardaron {len(agenda_data)} eventos en 'agenda.json' desde Rustico TV.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(obtener_agenda())
