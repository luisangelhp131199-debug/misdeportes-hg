import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import os

async def extraer_peliculas():
    url_base = "https://cliver.mom/"
    peliculas = []

    print(f"Conectando a {url_base}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            await page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Buscar las tarjetas o contenedores de películas
            items = soup.select(".item, .movie-item, article, .poster")

            for item in items[:30]:  # Extraer las primeras 30 películas
                link_tag = item.find("a")
                img_tag = item.find("img")
                title_tag = item.find(".title") or item.find("h2") or item.find("h3")

                if link_tag and img_tag:
                    title = title_tag.text.strip() if title_tag else img_tag.get("alt", "Sin título").strip()
                    poster = img_tag.get("data-src") or img_tag.get("src") or ""
                    link = link_tag.get("href") or ""

                    if link.startswith("/"):
                        link = url_base.rstrip("/") + link

                    if title and link:
                        peliculas.append({
                            "titulo": title,
                            "poster": poster,
                            "url": link
                        })

            print(f"Se encontraron {len(peliculas)} películas.")

            # Extraer servidor de reproductor para cada película encontrada
            for idx, pelicula in enumerate(peliculas):
                try:
                    print(f"[{idx+1}/{len(peliculas)}] Procesando: {pelicula['titulo']}")
                    await page.goto(pelicula['url'], wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)

                    p_content = await page.content()
                    p_soup = BeautifulSoup(p_content, "html.parser")

                    # Buscar iframe de video/embed
                    iframe = p_soup.find("iframe")
                    if iframe and iframe.get("src"):
                        embed_src = iframe.get("src")
                        if embed_src.startswith("//"):
                            embed_src = "https:" + embed_src
                        pelicula["embed_url"] = embed_src
                    else:
                        pelicula["embed_url"] = pelicula['url']

                except Exception as e:
                    print(f"Error procesando {pelicula['titulo']}: {e}")
                    pelicula["embed_url"] = pelicula['url']

        except Exception as e:
            print(f"Error general durante el scraping: {e}")

        await browser.close()

    # Filtrar solo las películas con datos completos
    peliculas_validas = [p for p in peliculas if "embed_url" in p]

    # Guardar resultados en JSON
    with open("peliculas.json", "w", encoding="utf-8") as f:
        json.dump(peliculas_validas, f, ensure_ascii=False, indent=2)

    print("Catálogo actualizado guardado en peliculas.json")

if __name__ == "__main__":
    asyncio.run(extraer_peliculas())
