import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument(r"user-data-dir=C:\Users\elmer\AppData\Local\Google\Chrome\User Data\SeleniumProfile")
    chrome_options.add_argument("profile-directory=Default")
    print("[DEBUG] Inicializando el driver de Chrome...")
    return webdriver.Chrome(options=chrome_options)

def obtener_botones_swipe(driver):
    print("[DEBUG] Buscando botones de swipe...")
    buttons = driver.find_elements(By.CSS_SELECTOR, 'button.gamepad-button')
    print(f"[DEBUG] Se encontraron {len(buttons)} botones con clase 'gamepad-button'")
    left_button, right_button = None, None
    for idx, btn in enumerate(buttons):
        print(f"[DEBUG] Analizando botón #{idx}")
        spans = btn.find_elements(By.CSS_SELECTOR, '.Hidden')
        print(f"[DEBUG]    -> Encontrados {len(spans)} spans '.Hidden'")
        for span in spans:
            label = span.text.strip().lower()
            print(f"[DEBUG]        -> Span con texto: '{label}'")
            if label == "no":
                left_button = btn
            elif label == "like":
                right_button = btn
    print(f"[DEBUG] Botón left: {bool(left_button)}, right: {bool(right_button)}")
    return left_button, right_button

def hacer_swipe(driver):
    left_button, right_button = obtener_botones_swipe(driver)
    if right_button and random.random() < 0.7:
        print("[DEBUG] Haciendo swipe RIGHT")
        right_button.click()
    elif left_button:
        print("[DEBUG] Haciendo swipe LEFT")
        left_button.click()
    else:
        print("[ERROR] No se encontraron botones de swipe")

def main():
    driver = iniciar_driver()
    driver.get('https://tinder.com/app/recs')
    print("[DEBUG] Esperando 10 segundos antes de comenzar a swipar...")
    time.sleep(10)

    while True:
        wait_time = random.randint(5, 10)
        print(f"[DEBUG] Esperando {wait_time}s antes del próximo swipe...")
        time.sleep(wait_time)
        try:
            hacer_swipe(driver)
        except Exception as e:
            print(f"[ERROR] No se pudo hacer swipe, esperando... {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
