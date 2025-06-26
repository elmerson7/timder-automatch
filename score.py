import requests
import cv2
import numpy as np
import mediapipe as mp

def descargar_imagen(url):
    try:
        resp = requests.get(url, timeout=10)
        img_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        return None

def medir_blur(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def analizar_landmarks(img):
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
        results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return None
        return results.multi_face_landmarks[0]

def simetria_facial(landmarks, w, h):
    puntos_pares = [
        (234, 454),  # mejillas
        (93, 323),   # cejas
        (61, 291),   # debajo ojos
        (78, 308),   # boca
    ]
    difs = []
    for izq, der in puntos_pares:
        lx, ly = int(landmarks.landmark[izq].x * w), int(landmarks.landmark[izq].y * h)
        rx, ry = int(landmarks.landmark[der].x * w), int(landmarks.landmark[der].y * h)
        dif = np.linalg.norm([lx - (w - rx), ly - ry])
        difs.append(dif)
    simetria = max(0, 10 - np.mean(difs)/5)
    return simetria

def proporcion_facial(landmarks, w, h):
    arriba = int(landmarks.landmark[10].y * h)
    abajo = int(landmarks.landmark[152].y * h)
    izq = int(landmarks.landmark[234].x * w)
    der = int(landmarks.landmark[454].x * w)
    alto = abajo - arriba
    ancho = der - izq
    proporcion = ancho / alto if alto else 0
    ideal = 0.75
    dif = abs(proporcion - ideal)
    score = max(0, 10 - dif*20)
    return score

def detectar_caras_open_cv(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return faces

def detectar_no_humano(landmarks):
    # Check para rostro tipo muñeca (ojos muy separados y boca baja)
    ojo_izq = landmarks.landmark[33]
    ojo_der = landmarks.landmark[263]
    boca = landmarks.landmark[13]
    menton = landmarks.landmark[152]
    dist_ojo = abs(ojo_der.x - ojo_izq.x)
    dist_boca = abs(boca.y - menton.y)
    # Valores experimentales, puedes ajustar según pruebas
    if dist_ojo > 0.45 or dist_boca > 0.30:
        return True
    return False

def analizar_imagen(url):
    img = descargar_imagen(url)
    motivos = []
    descartado = False
    score = 6  # Base: si tiene cara, buena calidad
    detalles = {}

    if img is None:
        motivos.append("No se pudo descargar la imagen")
        descartado = True
        return {"url": url, "score": 0, "descartado": True, "motivo": ", ".join(motivos), "detalles": detalles}

    blur_score = medir_blur(img)
    detalles["blur"] = blur_score

    faces = detectar_caras_open_cv(img)
    num_faces = len(faces)
    detalles["caras_detectadas"] = num_faces
    if num_faces == 0:
        motivos.append("No se detectó rostro")
        descartado = True
        score = 0
    if num_faces > 1:
        motivos.append("Se detectaron múltiples rostros")
        descartado = True
        score = 0

    landmarks = analizar_landmarks(img)
    if landmarks is None and num_faces == 1:
        motivos.append("No se detectaron landmarks faciales (rostro muy girado, oculto o no humano)")
        descartado = True
        score = 0

    if not descartado and landmarks is not None:
        h, w = img.shape[:2]
        detalles["landmarks_detectados"] = True

        # Check muñeca, anime, estatua...
        if detectar_no_humano(landmarks):
            motivos.append("Rostro detectado NO parece humano (posible muñeca, dibujo o estatua)")
            score = 0
            descartado = True

        # Simetría facial
        simetria = simetria_facial(landmarks, w, h)
        detalles["simetria"] = simetria
        if simetria < 5:
            motivos.append("Simetría facial baja")

        # Proporción facial
        proporcion = proporcion_facial(landmarks, w, h)
        detalles["proporcion"] = proporcion
        if proporcion < 5:
            motivos.append("Proporción facial fuera del rango óptimo")

        # Sumar puntos según calidad
        score += ((simetria-5)/5)*2
        score += ((proporcion-5)/5)*2

    # Penalizar blur
    if blur_score < 100:
        motivos.append("Imagen borrosa")
        score -= 2

    # Normalizar score
    score = max(0, min(10, round(score, 2)))

    if score < 5 and not descartado:
        motivos.append("Score bajo")
        descartado = True

    if not motivos and not descartado:
        motivo = "Aprobado"
    else:
        motivo = ", ".join(motivos)

    return {"url": url, "score": score, "descartado": descartado, "motivo": motivo, "detalles": detalles}

def analizar_perfil(urls):
    resultados = []
    scores = []
    for url in urls:
        res = analizar_imagen(url)
        resultados.append(res)
        scores.append(res["score"])
    score_general = round(np.mean(scores), 2)
    return {"score_general": score_general, "resultados": resultados}

# Ejemplo de uso:
if __name__ == "__main__":
    urls = [
        # Pega aquí tus urls de imágenes
        "https://i.pinimg.com/236x/6f/37/42/6f37425a7b8bdc754708ab4b73959a21.jpg",
        "https://i.pinimg.com/236x/1e/ea/28/1eea28748ad221dfd9bb41ef568e540e.jpg"
    ]
    resultado = analizar_perfil(urls)
    import json
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
