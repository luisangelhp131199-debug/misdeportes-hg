import base64
import json
import re
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def decodificar_url(url_embed):
    parsed = urlparse(url_embed)
    params = parse_qs(parsed.query)
    if "r" in params:
        b64_str = params["r"][0]
        try:
            missing_padding = len(b64_str) % 4
            if missing_padding:
                b64_str += "=" * (4 - missing_padding)
            return base64.b64decode(b64_str).decode("utf-8")
        except Exception:
            return url_embed
    return url_embed


def limpiar_texto(texto):
    texto = re.sub(r"[▶▼▲◄►]", "", texto)
    return " ".join(texto.split()).strip()


async def obtener_agenda():
    url = "https://futbollibretvhd.org/agenda"
    print("Iniciando extracción...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(4000)

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        agenda_data = []

        items = soup.find_all("li")

        for item in items:
            enlaces = item.find_all("a", href=True)
            if not enlaces:
                continue

            canales = []
            for a in enlaces:
                href = a["href"]
                texto_limpio = limpiar_texto(a.text)

                if len(texto_limpio) > 1 and not any(
                    x in href.lower()
                    for x in ["telegram", "facebook", "twitter", "javascript"]
                ):
                    link_completo = (
                        f"https://futbollibretvhd.org{href}"
                        if href.startswith("/")
                        else href
                    )
                    link_real = decodificar_url(link_completo)

                    canales.append(
                        {
                            "canal": texto_limpio,
                            "url_embed": link_completo,
                            "url_real": link_real,
                        }
                    )

            if canales:
                item_copy = BeautifulSoup(str(item), "html.parser")
                for a_tag in item_copy.find_all("a"):
                    a_tag.decompose()

                nombre_evento = limpiar_texto(item_copy.get_text())

                if nombre_evento:
                    agenda_data.append(
                        {"evento": nombre_evento, "opciones": canales}
                    )

        with open("agenda.json", "w", encoding="utf-8") as f:
            json.dump(agenda_data, f, ensure_ascii=False, indent=4)

        print(
            f"✅ Se guardaron {len(agenda_data)} eventos en 'agenda.json'."
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(obtener_agenda())
