import time
import random
import sqlite3
import cv2
import requests
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from deepface import DeepFace

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
        descripcion TEXT
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


def guardar_swipe(tipo, descripcion=None):
    timestamp = datetime.now()
    c.execute("INSERT INTO swipes (timestamp, tipo_swipe, descripcion) VALUES (?, ?, ?)",
            (timestamp, tipo, descripcion))
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

def imagen_es_valida(url_imagen):
    try:
        # Descargar imagen
        response = requests.get(url_imagen, timeout=10)
        if response.status_code != 200:
            print("[ERROR] No se pudo descargar la imagen.")
            return False

        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(response.content)
            path_local = tmp.name

        # Detectar rostro
        analisis = DeepFace.analyze(img_path=path_local, actions=["age"], enforce_detection=False)
        if not isinstance(analisis, list):
            analisis = [analisis]

        if len(analisis) != 1:
            print("[DESCARTADA] Cero o múltiples rostros.")
            return False

        # Verificar blur
        img = cv2.imread(path_local, cv2.IMREAD_GRAYSCALE)
        blur_score = cv2.Laplacian(img, cv2.CV_64F).var()
        if blur_score < 20:
            print(f"[DESCARTADA] Imagen borrosa (blur={blur_score:.2f})")
            return False

        print("[OK] Imagen válida")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def hacer_swipe(driver):
    time.sleep(1)
    cerrar_superlike_popup(driver)
    expandir_descripcion(driver)
    time.sleep(1)

    descripcion = obtener_descripcion(driver)

    if descripcion_contiene_palabra_excluida(driver):
        print("[BOT] Decisión: LEFT (palabra excluida en descripción)")
        swipe = 'nope'
    else:
        print("[BOT] Decisión: RIGHT (perfil aceptado)")
        swipe = 'like'

    # Obtener imágenes del perfil ANTES de esperar
    urls_crudas = obtener_urls_imagenes(driver)
    # print(f"[DEBUG] URLs obtenidas del perfil: {urls_crudas}")

    urls_validas = []
    for url in urls_crudas:
        print(f"\n[VERIFICANDO] {url}")
        if imagen_es_valida(url):
            print(f"[✅ VÁLIDA] Imagen aceptada: {url}")
            urls_validas.append(url)
        else:
            print(f"[❌ DESCARTADA] Imagen rechazada: {url}")

    # Espera personalizada
    wait_time = random.randint(6, 10)
    print(f"[DEBUG] Esperando {wait_time}s antes de hacer swipe...")
    time.sleep(wait_time)

    # Ejecutar swipe y guardar
    if swipe == 'nope':
        time.sleep(6)
    else:
        time.sleep(7)

    # Ejecutar swipe y guardar
    if swipe == 'nope':
        left_button, _ = obtener_botones_swipe(driver)
        if left_button:
            left_button.click()
            print("[BOT] Swipe LEFT ejecutado")
            guardar_swipe('nope', descripcion)
        else:
            print("[ERROR] No se encontró el botón de left swipe")
    else:
        _, right_button = obtener_botones_swipe(driver)
        if right_button:
            right_button.click()
            print("[BOT] Swipe RIGHT ejecutado")
            guardar_swipe('like', descripcion)
        else:
            print("[ERROR] No se encontró el botón de right swipe")

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
