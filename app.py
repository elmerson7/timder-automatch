import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

EXCLUSION_KEYWORDS = [
    "trans", "transgénero", "transgénera", "persona transfemenina", "persona transmasculina",
    "transfemenina", "transmasculina", "transexual", "transsexual", "travesti", "no binario",
    "no binaria", "género fluido", "gender fluid", "género queer", "queer", "agénero",
    "bigénero", "pangénero", "dos espíritus", "two-spirit", "andrógino", "andrógina",
    "persona trans", "persona no binaria", "persona de género no conforme", "otro"
]


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

def hacer_swipe(driver):
    expandir_descripcion(driver)  # Primero, expande descripción
    
    if descripcion_contiene_palabra_excluida(driver):
        print("[BOT] Swipe LEFT (palabra excluida en descripción)")
        # Buscar el botón justo antes de usarlo
        left_button, _ = obtener_botones_swipe(driver)
        if left_button:
            left_button.click()
        else:
            print("[ERROR] No se encontró el botón de left swipe")
    else:
        print("[BOT] Swipe RIGHT (perfil aceptado)")
        # Buscar el botón justo antes de usarlo
        _, right_button = obtener_botones_swipe(driver)
        if right_button:
            right_button.click()
        else:
            print("[ERROR] No se encontró el botón de right swipe")

def main():
    driver = iniciar_driver()
    driver.get('https://tinder.com/app/recs')
    print("[DEBUG] Esperando 10 segundos antes de comenzar a swipar...")
    time.sleep(10)

    while True:
        wait_time = 12
        print(f"[DEBUG] Esperando {wait_time}s antes del próximo swipe...")
        time.sleep(wait_time)
        try:
            hacer_swipe(driver)
        except Exception as e:
            print(f"[ERROR] No se pudo hacer swipe, esperando... {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
