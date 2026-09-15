import asyncio
import json
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

def limpiar_texto(texto):
    texto = re.sub(r"[▶▼▲◄►•]", "", texto)
    return " ".join(texto.split()).strip()

async def obtener_agenda():
    url = "https://rusticotv.la/"
    print("Iniciando extracción robusta de agenda desde Rustico TV...")

    async with async_playwright() as p:
        # Usamos un navegador visible o headless con argumentos para evitar bloqueos básicos
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            # Esperamos a que los elementos dinámicos o la tabla/grilla de partidos aparezcan
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"❌ Error al cargar la página: {e}")
            await browser.close()
            return

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        agenda_data = []

        # ESTRATEGIA NUEVA: 
        # En lugar de buscar clases estrictas, buscamos cualquier elemento contenedor 
        # que tenga enlaces internos (que suelen ser los canales o el partido)
        # Probamos primero con filas de tablas, divs de eventos o artículos.
        candidatos = soup.find_all(["tr", "div", "article", "li"])
        print(f"🔍 Analizando {len(candidatos)} elementos en el DOM...")

        for cont in candidatos:
            # Buscamos enlaces dentro del contenedor que parezcan canales o transmisiones
            enlaces = cont.find_all("a", href=True)
            if not enlaces:
                continue

            canales = []
            for a in enlaces:
                href = a["href"]
                texto_canal = limpiar_texto(a.text)

                # Descartamos redes sociales, menús o enlaces vacíos
                excluir = ["telegram", "whatsapp", "facebook", "twitter", "instagram", "javascript", "#", "inicio", "contacto", "dmca", "aviso"]
                if len(texto_canal) > 1 and not any(x in href.lower() or x in texto_canal.lower() for x in excluir):
                    
                    if href.startswith("/"):
                        link_completo = f"https://rusticotv.la{href}"
                    elif href.startswith("http"):
                        link_completo = href
                    else:
                        continue
                    
                    canales.append({
                        "canal": texto_canal,
                        "url_embed": link_completo
                    })

            # Si encontramos canales válidos en este bloque, procedemos a sacar el nombre del evento
            if len(canales) > 0:
                cont_copy = BeautifulSoup(str(cont), "html.parser")
                for a_tag in cont_copy.find_all("a"):
                    a_tag.decompose() # Quitamos los botones de canales para dejar solo el texto del partido

                nombre_evento = limpiar_texto(cont_copy.get_text())

                # Validamos que el texto del evento parezca un partido (que tenga longitud razonable y no sea texto basura de la web)
                if 5 < len(nombre_evento) < 200:
                    # Limpiamos duplicados exactos en nuestra lista
                    if not any(e["evento"] == nombre_evento for e in agenda_data):
                        agenda_data.append({
                            "evento": nombre_evento,
                            "opciones": canales
                        })

        await browser.close()

        # Guardado en JSON
        with open("agenda.json", "w", encoding="utf-8") as f:
            json.dump(agenda_data, f, ensure_ascii=False, indent=4)

        print(f"✅ ¡Proceso finalizado! Se guardaron {len(agenda_data)} eventos en 'agenda.json'.")

if __name__ == "__main__":
    asyncio.run(obtener_agenda())
