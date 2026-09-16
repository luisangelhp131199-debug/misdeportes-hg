import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re

async def extraer_peliculas_mundialtv():
    url_base = "https://mundialtvweb.blogspot.com/?m=1"
    peliculas = []

    print(f"Conectando a {url_base}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            await page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Selector típico para las entradas de publicaciones en Blogger
            posts = soup.select(".post, .post-outer, article, .blog-item")
            print(f"Entradas encontradas en el blog: {len(posts)}")

            for post in posts[:30]:  # Tomamos las primeras 30 publicaciones
                link_tag = post.find("a")
                img_tag = post.find("img")
                title_tag = post.find("h3") or post.find("h2") or post.find(class_="post-title")

                if link_tag and img_tag:
                    title = title_tag.get_text(strip=True) if title_tag else (img_tag.get("alt") or "Sin título").strip()
                    poster = img_tag.get("data-src") or img_tag.get("src") or ""
                    link = link_tag.get("href") or ""

                    if title and link and "Sin título" not in title:
                        peliculas.append({
                            "titulo": title,
                            "poster": poster,
                            "url": link
                        })

            # Eliminar duplicados basándose en el enlace
            peliculas_unicas = {p['url']: p for p in peliculas}.values()
            peliculas = list(peliculas_unicas)
            print(f"Se procesarán {len(peliculas)} películas/videos únicos.")

            # Entrar a cada enlace para buscar el archivo .mp4 directo
            for idx, pelicula in enumerate(peliculas):
                try:
                    print(f"[{idx+1}/{len(peliculas)}] Buscando MP4 en: {pelicula['titulo']}")
                    await page.goto(pelicula['url'], wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)

                    p_content = await page.content()
                    p_soup = BeautifulSoup(p_content, "html.parser")

                    mp4_url = ""

                    # 1. Buscar en etiquetas <source> o <video>
                    source_tag = p_soup.find("source", type="video/mp4") or p_soup.find("video")
                    if source_tag and source_tag.get("src"):
                        mp4_url = source_tag.get("src")

                    # 2. Si no hay etiqueta video directa, buscar mediante Expresión Regular en el código fuente (muy útil en Blogspot)
                    if not mp4_url:
                        match = re.search(r'https?://[^\s<>"]+?\.mp4', p_content)
                        if match:
                            mp4_url = match.group(0)

                    # Asignar el enlace .mp4 encontrado, o dejar la URL de respaldo si no hay MP4 visible
                    pelicula["embed_url"] = mp4_url if mp4_url else pelicula['url']

                except Exception as e:
                    print(f"Error procesando {pelicula['titulo']}: {e}")
                    pelicula["embed_url"] = pelicula['url']

        except Exception as e:
            print(f"Error general durante el scraping: {e}")

        await browser.close()

    # Guardar en peliculas.json
    with open("peliculas.json", "w", encoding="utf-8") as f:
        json.dump(peliculas, f, ensure_ascii=False, indent=2)

    print("¡Proceso finalizado! Archivo peliculas.json actualizado con éxito.")

if __name__ == "__main__":
    asyncio.run(extraer_peliculas_mundialtv())
