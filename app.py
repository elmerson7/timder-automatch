import time
import random
import sqlite3
import cv2
import requests
import tempfile
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from deepface import DeepFace
from openai import analizar_imagen_openai

EXCLUSION_KEYWORDS = [
    "trans", "transgénero", "transgénera", "persona transfemenina", "persona transmasculina",
    "transfemenina", "transmasculina", "transexual", "transsexual", "travesti", "no binario",
    "no binaria", "género fluido", "gender fluid", "género queer", "queer", "agénero",
    "bigénero", "pangénero", "dos espíritus", "two-spirit", "andrógino", "andrógina",
    "persona trans", "persona no binaria", "persona de género no conforme", "🏳️‍🌈"
]

# --- Conexion y creación de BD y tablas ---
conn = sqlite3.connect('timder.db')
c = conn.cursor()

# Crear tabla swipes si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS swipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        tipo_swipe TEXT,
        descripcion TEXT,
        imagenes_urls TEXT,
        analisis_json TEXT
    )
''')

# Crear tabla logs si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inicio DATETIME
    )
''')

# Guardar inicio de sesión
c.execute("INSERT INTO logs (inicio) VALUES (?)", (datetime.now(),))
conn.commit()


def guardar_swipe(tipo, descripcion=None, urls=None, analisis=None):
    timestamp = datetime.now()
    urls_str = json.dumps(urls) if urls else None
    analisis_str = json.dumps(analisis) if analisis else None
    c.execute("INSERT INTO swipes (timestamp, tipo_swipe, descripcion, imagenes_urls, analisis_json) VALUES (?, ?, ?, ?, ?)",
              (timestamp, tipo, descripcion, urls_str, analisis_str))
    conn.commit()


def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument(r"user-data-dir=C:\Users\elmer\AppData\Local\Google\Chrome\User Data\SeleniumProfile")
    chrome_options.add_argument("profile-directory=Default")
    print("[DEBUG] Inicializando el driver de Chrome...")
    return webdriver.Chrome(options=chrome_options)

def obtener_botones_swipe(driver):
    buttons = driver.find_elements(By.CSS_SELECTOR, 'button.gamepad-button')
    left_button, right_button = None, None
    for btn in buttons:
        spans = btn.find_elements(By.CSS_SELECTOR, '.Hidden')
        for span in spans:
            label = span.text.strip().lower()
            if label == "no":
                left_button = btn
            elif label == "like":
                right_button = btn
    return left_button, right_button

def expandir_descripcion(driver):
    try:
        # Enviamos la flecha arriba al body
        body = driver.find_element(By.TAG_NAME, 'body')
        body.send_keys(Keys.ARROW_UP)
        print("[DEBUG] Tecla flecha ARRIBA enviada para expandir descripción.")
        time.sleep(1)  # Espera que se despliegue la descripción
    except Exception as e:
        print(f"[WARN] No se pudo enviar la flecha arriba: {e}")

def obtener_descripcion(driver):
    descripcion_final = []
    try:
        descripciones = driver.find_elements(By.CSS_SELECTOR, '.C\\(\\$c-ds-text-primary\\).Typs\\(body-1-regular\\)')
        for desc in descripciones:
            texto = desc.text.strip()
            descripcion_final.append(texto)
    except Exception as e:
        print(f"[WARN] No se pudo leer la descripción: {e}")
    return " | ".join(descripcion_final)

def descripcion_contiene_palabra_excluida(driver):
    try:
        descripciones = driver.find_elements(By.CSS_SELECTOR, '.C\\(\\$c-ds-text-primary\\).Typs\\(body-1-regular\\)')
        for desc in descripciones:
            texto = desc.text.lower()
            print(f"[DEBUG] Descripción encontrada: {texto}")
            if any(word in texto for word in EXCLUSION_KEYWORDS):
                print("[DEBUG] Palabra excluida encontrada en la descripción.")
                return True
    except Exception as e:
        print(f"[WARN] No se pudo leer la descripción: {e}")
    return False

def cerrar_superlike_popup(driver):
    try:
        botones = driver.find_elements(By.XPATH, '//button[contains(.,"No, gracias")]')
        if botones:
            botones[0].click()
            print("[BOT] Popup de Super Like cerrado con 'No, gracias'")
            time.sleep(1)
        else:
            print("[DEBUG] No hay popup de Super Like que cerrar")
    except Exception as e:
        print(f"[WARN] No se pudo cerrar el popup de Super Like: {e}")

def obtener_urls_imagenes(driver):
    urls = set()
    ya_vistos = set()

    while True:
        try:
            slides = driver.find_elements(By.CSS_SELECTOR, 'div[id^="carousel-item-"][aria-hidden="false"]')
            for slide in slides:
                style_divs = slide.find_elements(By.CSS_SELECTOR, 'div[style*="background-image"]')
                for div in style_divs:
                    style = div.get_attribute('style')
                    if 'background-image' in style:
                        inicio = style.find('url("') + 5
                        fin = style.find('")', inicio)
                        url = style[inicio:fin]
                        urls.add(url)

            current_ids = {slide.get_attribute("id") for slide in slides}
            if current_ids.issubset(ya_vistos):
                break
            ya_vistos.update(current_ids)

            boton_siguiente = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Siguiente foto"]')
            boton_siguiente.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"[WARN] Error al obtener imágenes: {e}")
            break

    return list(urls)

import os
import requests
import cv2
from urllib.parse import urlparse
from deepface import DeepFace
from cv2 import IMREAD_GRAYSCALE, CV_64F, Laplacian

def imagen_es_valida(url_imagen):
    resultado = {
        "url": url_imagen,
        "valida": False,
        "razon": "",
        "score": None,
        "json": None
    }

    try:
        # Crear carpeta img_tmp si no existe
        os.makedirs("img_tmp", exist_ok=True)

        # Obtener nombre del archivo desde la URL
        nombre_archivo = os.path.basename(urlparse(url_imagen).path)
        path_local = os.path.join("img_tmp", nombre_archivo)

        # Descargar imagen a img_tmp/
        response = requests.get(url_imagen, timeout=10)
        if response.status_code != 200:
            resultado["razon"] = "No se pudo descargar"
            return resultado

        with open(path_local, "wb") as f:
            f.write(response.content)

        # Análisis con DeepFace
        analisis = DeepFace.analyze(img_path=path_local, actions=["age"], enforce_detection=False)
        if not isinstance(analisis, list):
            analisis = [analisis]

        if len(analisis) != 1:
            resultado["razon"] = "Cero o múltiples rostros"
            return resultado

        # Verificar desenfoque
        img = cv2.imread(path_local, IMREAD_GRAYSCALE)
        blur_score = Laplacian(img, CV_64F).var()
        if blur_score < 20:
            resultado["razon"] = f"Imagen borrosa (blur={blur_score:.2f})"
            return resultado

        # Análisis con OpenAI
        resultado["valida"] = True
        resultado["razon"] = "Válida"

        json_result = analizar_imagen_openai(path_local)
        if json_result and isinstance(json_result, dict):
            score = json_result.get("score_general", 0)
            if score > 0:
                resultado["score"] = score
                resultado["json"] = json_result
            else:
                resultado["razon"] = "Score 0 (descartada por OpenAI)"
                resultado["valida"] = False
        else:
            resultado["razon"] = "OpenAI no devolvió JSON"

        return resultado

    except Exception as e:
        resultado["razon"] = f"Excepción: {e}"
        return resultado


def hacer_swipe(driver):
    time.sleep(1)
    cerrar_superlike_popup(driver)
    expandir_descripcion(driver)
    time.sleep(1)

    descripcion = obtener_descripcion(driver)

    if descripcion_contiene_palabra_excluida(driver):
        print("[BOT] Decisión: LEFT (palabra excluida en descripción)")
        urls_crudas = obtener_urls_imagenes(driver)
        resultados = [imagen_es_valida(url) for url in urls_crudas]
        guardar_swipe('nope', descripcion, urls=urls_crudas, analisis=resultados)
        left_button, _ = obtener_botones_swipe(driver)
        if left_button:
            left_button.click()
        return

    urls_crudas = obtener_urls_imagenes(driver)
    resultados_validos = []
    score_total = 0
    score_count = 0

    for url in urls_crudas:
        print(f"[VERIFICANDO] {url}")
        resultado = imagen_es_valida(url)
        if resultado["valida"] and resultado["score"] is not None:
            score_total += resultado["score"]
            score_count += 1
        resultados_validos.append(resultado)

    promedio = score_total / score_count if score_count > 0 else 0
    print(f"[DEBUG] Promedio de score: {promedio}")

    decision = 'like' if promedio >= 5.5 else 'nope'
    print(f"[BOT] Decisión final por score: {decision.upper()}")

    wait_time = random.randint(6, 10)
    print(f"[DEBUG] Esperando {wait_time}s antes de hacer swipe...")
    time.sleep(wait_time)

    if decision == 'nope':
        left_button, _ = obtener_botones_swipe(driver)
        if left_button:
            left_button.click()
            print("[BOT] Swipe LEFT ejecutado")
        else:
            print("[ERROR] No se encontró el botón de left swipe")
    else:
        _, right_button = obtener_botones_swipe(driver)
        if right_button:
            right_button.click()
            print("[BOT] Swipe RIGHT ejecutado")
        else:
            print("[ERROR] No se encontró el botón de right swipe")

    guardar_swipe(decision, descripcion, urls=urls_crudas, analisis=resultados_validos)

def main():
    driver = iniciar_driver()
    driver.get('https://tinder.com/app/recs')
    print("[DEBUG] Esperando 10 segundos antes de comenzar a swipar...")
    time.sleep(10)

    while True:
        try:
            hacer_swipe(driver)
        except Exception as e:
            print(f"[ERROR] No se pudo hacer swipe, esperando... {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
