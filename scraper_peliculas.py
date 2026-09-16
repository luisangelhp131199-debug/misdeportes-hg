import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re

async def extraer_todo_el_catalogo():
    url_base = "https://mundialtvweb.blogspot.com"
    peliculas_dict = {} # Usamos un diccionario con la URL como clave para evitar duplicados
    
    urls_a_visitar = {url_base + "/?m=1"}
    urls_visitadas = set()

    print("Iniciando escaneo exhaustivo de MundialTV (Categorías + Paginación)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Paso 1: Descubrir todas las categorías, etiquetas y páginas de la web
        while urls_a_visitar:
            url_actual = urls_a_visitar.pop()
            if url_actual in urls_visitadas:
                continue
            
            urls_visitadas.add(url_actual)
            print(f"Explorando sección/etiqueta: {url_actual}")

            try:
                await page.goto(url_actual, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Scroll hacia abajo para forzar la carga de elementos dinámicos
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # A. Extraer todas las tarjetas de películas/series visibles en esta página
                tarjetas = soup.select("a[href*='/202'], a[href*='.html']")
                for tarjeta in tarjetas:
                    link = tarjeta.get("href")
                    if link and "mundialtvweb.blogspot.com" in link and not "search/label" in link:
                        link_limpio = link.split("?")[0]
                        
                        # Extraer imagen y título
                        img_tag = tarjeta.find("img") or tarjeta.select_one("img")
                        title = ""
                        if img_tag and img_tag.get("alt"):
                            title = img_tag.get("alt")
                        else:
                            title_elem = tarjeta.find(class_=re.compile("title|info|nombre", re.I))
                            title = title_elem.get_text(strip=True) if title_elem else tarjeta.get_text(strip=True)

                        if link_limpio and len(link_limpio) > 35 and link_limpio not in peliculas_dict:
                            poster = ""
                            if img_tag:
                                poster = img_tag.get("data-src") or img_tag.get("src") or ""
                            
                            if title and len(title) > 2:
                                peliculas_dict[link_limpio] = {
                                    "titulo": title,
                                    "poster": poster,
                                    "url": link_limpio
                                }

                # B. Buscar enlaces de categorías o etiquetas (ej. /search/label/...) para agregarlas a la cola
                enlaces_etiquetas = soup.select("a[href*='/search/label/'], a.blog-pager-older-link, a[class*='button'], a[href*='max-results']")
                for etq in enlaces_etiquetas:
                    e_link = etq.get("href")
                    if e_link:
                        if e_link.startswith("/"):
                            e_link = url_base + e_link
                        if "mundialtvweb.blogspot.com" in e_link and e_link not in urls_visitadas:
                            urls_a_visitar.add(e_link)

            except Exception as e:
                print(f"Error explorando {url_actual}: {e}")

        lista_peliculas = list(peliculas_dict.values())
        print(f"\n¡Se encontraron {len(lista_peliculas)} contenidos únicos (Películas/Series) en total!")
        print("Extrayendo enlaces de video directos (.mp4 o fuente) de cada uno...")

        # Paso 2: Entrar a cada enlace individual para extraer el reproductor o enlace de video real
        for idx, pelicula in enumerate(lista_peliculas):
            try:
                print(f"[{idx+1}/{len(lista_peliculas)}] Extrayendo video: {pelicula['titulo']}")
                await page.goto(pelicula['url'], wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(800)

                p_content = await page.content()
                p_soup = BeautifulSoup(p_content, "html.parser")

                mp4_url = ""

                # Buscar etiquetas de video nativas o de iframe embebido
                source_tag = p_soup.find("source", type="video/mp4") or p_soup.find("video")
                if source_tag and source_tag.get("src"):
                    mp4_url = source_tag.get("src")

                # Si no está directo, buscar iframes o reproductores externos integrados
                if not mp4_url:
                    iframe_tag = p_soup.find("iframe")
                    if iframe_tag and iframe_tag.get("src"):
                        mp4_url = iframe_tag.get("src")

                # Búsqueda por patrón de texto por si viene en un script JSON interno
                if not mp4_url:
                    match = re.search(r'https?://[^\s<>"]+?\.(?:mp4|m3u8)', p_content)
                    if match:
                        mp4_url = match.group(0)

                pelicula["embed_url"] = mp4_url if mp4_url else pelicula['url']

            except Exception as e:
                print(f"No se pudo extraer el video de {pelicula['titulo']}: {e}")
                pelicula["embed_url"] = pelicula['url']

        await browser.close()

    # Guardar el resultado completo en peliculas.json
    with open("peliculas.json", "w", encoding="utf-8") as f:
        json.dump(lista_peliculas, f, ensure_ascii=False, indent=2)

    print("\n¡Listo! Catálogo completo guardado exitosamente en peliculas.json con todas las categorías.")

if __name__ == "__main__":
    asyncio.run(extraer_todo_el_catalogo())
