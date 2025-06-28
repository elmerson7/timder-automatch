import cv2
import requests
import tempfile
from deepface import DeepFace

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
        if blur_score < 40:
            print(f"[DESCARTADA] Imagen borrosa (blur={blur_score:.2f})")
            return False

        print("[OK] Imagen válida")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

url = "https://randomuser.me/api/portraits/women/30.jpg"

resultado = imagen_es_valida(url)
print("¿Enviar a API?", resultado)
