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
    except:
        return None

def medir_blur(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def detectar_rostro_mediapipe(img):
    mp_face_detection = mp.solutions.face_detection
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_detection.process(img_rgb)
        if not results.detections:
            return []
        return results.detections

def seleccionar_cara_principal(detecciones):
    mayor = None
    area_mayor = 0
    for det in detecciones:
        box = det.location_data.relative_bounding_box
        area = box.width * box.height
        if area > area_mayor:
            area_mayor = area
            mayor = det
    return mayor

def analizar_landmarks(img):
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
        results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return None
        return results.multi_face_landmarks[0]

def simetria_facial(landmarks, w, h):
    puntos_pares = [(234, 454), (93, 323), (61, 291), (78, 308)]
    difs = []
    for izq, der in puntos_pares:
        lx, ly = int(landmarks.landmark[izq].x * w), int(landmarks.landmark[izq].y * h)
        rx, ry = int(landmarks.landmark[der].x * w), int(landmarks.landmark[der].y * h)
        dif = np.linalg.norm([lx - (w - rx), ly - ry])
        difs.append(dif)
    return max(0, 10 - np.mean(difs)/5)

def proporcion_facial(landmarks, w, h):
    arriba = int(landmarks.landmark[10].y * h)
    abajo = int(landmarks.landmark[152].y * h)
    izq = int(landmarks.landmark[234].x * w)
    der = int(landmarks.landmark[454].x * w)
    alto = abajo - arriba
    ancho = der - izq
    proporcion = ancho / alto if alto else 0
    ideal = 0.75
    return proporcion, max(0, 10 - abs(proporcion - ideal) * 20)

def detectar_no_humano(landmarks):
    ojo_izq = landmarks.landmark[33]
    ojo_der = landmarks.landmark[263]
    boca = landmarks.landmark[13]
    menton = landmarks.landmark[152]
    dist_ojo = abs(ojo_der.x - ojo_izq.x)
    dist_boca = abs(boca.y - menton.y)
    return dist_ojo > 0.45 or dist_boca > 0.30

def analizar_cuerpo(img):
    mp_pose = mp.solutions.pose
    with mp_pose.Pose(static_image_mode=True) as pose:
        results = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not results.pose_landmarks:
            return None, None
        landmarks = results.pose_landmarks.landmark
        try:
            ancho_cadera = abs(landmarks[mp_pose.PoseLandmark.LEFT_HIP].x - landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x)
            altura = abs(landmarks[mp_pose.PoseLandmark.NOSE].y - landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y)
            proporcion = ancho_cadera / altura if altura > 0 else 0
            es_robusto = proporcion > 0.20  # Más estricto
            return proporcion, es_robusto
        except:
            return None, None

def evaluar_ancho_cara(landmarks, w, h):
    izq = landmarks.landmark[234].x * w
    der = landmarks.landmark[454].x * w
    alto = abs(landmarks.landmark[10].y * h - landmarks.landmark[152].y * h)
    ancho = abs(der - izq)
    proporcion = ancho / alto if alto else 0
    return proporcion > 0.85, proporcion

def analizar_imagen(url):
    img = descargar_imagen(url)
    motivos = []
    detalles = {}
    descartado = False
    score = 6

    if img is None:
        return {"url": url, "score": 0, "descartado": True, "motivo": "No se pudo descargar la imagen", "detalles": detalles}

    h, w = img.shape[:2]
    blur_score = medir_blur(img)
    detalles["blur"] = blur_score

    detecciones = detectar_rostro_mediapipe(img)
    detalles["caras_detectadas"] = len(detecciones)

    if len(detecciones) == 0:
        motivos.append("No se detectó rostro")
        return {"url": url, "score": 0, "descartado": True, "motivo": ", ".join(motivos), "detalles": detalles}

    cara_principal = seleccionar_cara_principal(detecciones)
    landmarks = analizar_landmarks(img)

    if not landmarks:
        motivos.append("No se detectaron landmarks faciales")
        descartado = True
        score = 0

    if landmarks and not descartado:
        detalles["landmarks_detectados"] = True

        if detectar_no_humano(landmarks):
            motivos.append("Rostro no parece humano")
            score = 0
            descartado = True

        sim = simetria_facial(landmarks, w, h)
        detalles["simetria"] = sim
        if sim < 5:
            motivos.append("Simetría facial baja")
        score += ((sim - 5) / 5) * 2

        prop_valor, prop_score = proporcion_facial(landmarks, w, h)
        detalles["proporcion_facial"] = prop_valor
        if prop_score < 5:
            motivos.append("Proporción facial fuera de lo ideal")
        if prop_valor > 1.2:
            motivos.append("Proporción facial artificialmente alta")
            score -= 1
        score += ((prop_score - 5) / 5) * 2

        # Cara ancha
        es_ancha, propor_ancha = evaluar_ancho_cara(landmarks, w, h)
        detalles["proporcion_ancho_cara"] = round(propor_ancha, 2)
        if es_ancha:
            motivos.append("Ancho facial elevado")
            score -= 1.5
            detalles["cara_ancha"] = True

    # Cuerpo
    prop_cuerpo, es_robusto = analizar_cuerpo(img)
    if prop_cuerpo:
        detalles["proporcion_cuerpo"] = round(prop_cuerpo, 3)
        if es_robusto:
            motivos.append("Cuerpo robusto")
            score -= 1.5
        else:
            score += 0.5

    if blur_score < 100:
        motivos.append("Imagen borrosa")
        score -= 2

    score = max(0, min(10, round(score, 2)))
    if score < 5 and not descartado:
        motivos.append("Score bajo")
        descartado = True

    return {
        "url": url,
        "score": score,
        "descartado": descartado,
        "motivo": ", ".join(motivos) if motivos else "Aprobado",
        "detalles": detalles
    }

def analizar_perfil(urls):
    resultados = []
    scores = []
    for url in urls:
        res = analizar_imagen(url)
        resultados.append(res)
        scores.append(res["score"])
    score_general = round(np.mean(scores), 2) if scores else 0
    return {"score_general": score_general, "resultados": resultados}

# Ejemplo de uso:
if __name__ == "__main__":
    urls = [
        # Agrega aquí tus URLs de prueba
        "https://images-ssl.gotinder.com/u/n89cjCGYb8KxgdonXKWPeg/s46MCQJoaUoHof3KJp5aiT.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS9uODljakNHWWI4S3hnZG9uWEtXUGVnLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=y-oXAiaRBza4pv-PqLu9M52XIqJPdAaLvracds7XCKnNxjjMYHcW3y5xPNW~TuJae8nOhC8zDZiGSqFOT9SlhboG-VwnWIanOUU7YWRAVZV6GEN6ofMXP2opLEciJllMfW4ElXf8XRE~DjdNbvLbjYkKQNSmsz89XmWrqH5nJJagLlJ27leYdjBFXH3H19sIbuWFVsc192~O9JqVhEVV3CzxJlZDh8mxlY4qEvlCEcmZ8IF5mEvJVbL~7NAwve27A7dDVNl30XHttpUIsJXm9tC6jbAJcRJuSia~w5tBZ20ere-MFr8rKM4NpYor3OED-RitYwcNFPMk9vsjMZPDug__&Key-Pair-Id=K368TLDEUPA6OI",
        "https://images-ssl.gotinder.com/u/9nsrsUcRCARK57TYSzxfjD/i9ejTi8ubtF5nqrSubrxFt.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS85bnNyc1VjUkNBUks1N1RZU3p4ZmpELyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=lICo6t81j~Kq8aglsXyWgGLnXNsXma~-biVgnHyyr-MXol3QhSwBF6GWcrgd4280u~r65T6HigoshAhX4IeGUqUrWP4C3L~NK4wXbhneqwtyCqN~w0vA5lRwF9IH9gMuV6BAGzigN7iqxV65tqTGj6qPp3SR790YRZYHRphlCYnEiQJgTHxRovP2L7PyrAG11uTmlMdJpZ6u3Yh~xWTeTwuXekcHr6OUEu7ZdU0EKogFju96dkwBhY4MhdaHQ8p9JlcA6jTIdllHCNcAugVyC8gRTk1kAwwKJ3iQ6ADknJzRXO14vW57a1vL3P1Bl37UbXlLAVq6SLR-y-Sf0R5OkA__&Key-Pair-Id=K368TLDEUPA6OI",
        "https://images-ssl.gotinder.com/u/kn7EVquMLh2WAQVnsFUAAK/jeQHUgUUmfLPBF2vDV6TU4.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS9rbjdFVnF1TUxoMldBUVZuc0ZVQUFLLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=gdMAR0cHqO92RD8KH2NHvQE2-RwQX7OrvbYNcnxsTZci6YW5giO515gaMzRj7uUwMnnHYLlPjSVOPON3PtJPtRJV9MRpx90adJJdyzCDYD3RlVGzcwcoGsqcRkD~-o1GSHgeDNBNj00sWq45UJCUAlAZNbz4u2IUq9G5BDtLCCOaHLnxvIy9Zn6ga0SyVRo7PaGqc52mPR-TXJ39h-rtBYsax3kg1IhjM~Jxs9zaioziIJvlFeAbfNFO1VhpgglQJsidOSvtzExNgKX4h~hMwmD0U972xQ~rZWEOaxrx4egg2uCrDbzgSmtpXWWaneEqQHnEMbqiNm-TTk49YXAQ8g__&Key-Pair-Id=K368TLDEUPA6OI",
        "https://images-ssl.gotinder.com/u/mt1Z67pJUkLVUWqDXhRRXN/iaM1Ep6Fc12bdbbprvdKKe.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS9tdDFaNjdwSlVrTFZVV3FEWGhSUlhOLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=0O~TLZqj5BY5-YDkbdlJ06cFU4myeU9SHbC~1ZCL4oZJua259BOqffmDVo-vS7ovMsoiYja4Pk8JI22TDivXbaXcORaFPDpaRUlJ2Vg6m34HtlrpzCkhe5-z5Bo5CvZCMo-50w~ZMGDSz38-cw~qLOo58jWbcrzxoi6XxQelhP45Eqj340vvX6PsFga-VxOnroDE8e4qRFCR1QZ8gSJiR68ut4x~WvFVS7OPwk0V-VzA01jYrBvX5Ty3BeuqFqYKdMb7UenksxXqKNaNIn2vSszepHd75oovKwyIlBt35Ea6skCMLMCPZusbPhnZ8IuiDuZ~yJjHTpBrr3r4J~62ww__&Key-Pair-Id=K368TLDEUPA6OI",
        "https://images-ssl.gotinder.com/u/mt1Z67pJUkLVUWqDXhRRXN/iaM1Ep6Fc12bdbbprvdKKe.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS9tdDFaNjdwSlVrTFZVV3FEWGhSUlhOLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=0O~TLZqj5BY5-YDkbdlJ06cFU4myeU9SHbC~1ZCL4oZJua259BOqffmDVo-vS7ovMsoiYja4Pk8JI22TDivXbaXcORaFPDpaRUlJ2Vg6m34HtlrpzCkhe5-z5Bo5CvZCMo-50w~ZMGDSz38-cw~qLOo58jWbcrzxoi6XxQelhP45Eqj340vvX6PsFga-VxOnroDE8e4qRFCR1QZ8gSJiR68ut4x~WvFVS7OPwk0V-VzA01jYrBvX5Ty3BeuqFqYKdMb7UenksxXqKNaNIn2vSszepHd75oovKwyIlBt35Ea6skCMLMCPZusbPhnZ8IuiDuZ~yJjHTpBrr3r4J~62ww__&Key-Pair-Id=K368TLDEUPA6OI",
        "https://images-ssl.gotinder.com/u/vn8LRqJNwrkm8f7f8pLqnD/5fzv3dL9zG33MksM7VAQnS.webp?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6IiovdS92bjhMUnFKTndya204ZjdmOHBMcW5ELyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NTE2NDk5NjZ9fX1dfQ__&Signature=eOVsIDIPZL91pTsHe0R9XZ80NcUu8ZE6GnhW-mwm~G6PB04LoAEaG0~2gje1CkREime1X41VUe7gaZjoYxNsdlWivuo5B4lAqlDw7v5iC5n41FKTOpr2l3umK5eRvjQTPv7UwjYQHeunx7CcCQlU82MBF95aXFHmVY4tgVScprXK4qKW95PAzoSH84Ou2n-WWNSDi8qv9bryA583z1TCRzjkAzCYGneg0FdXrXgWu-IoV1UgKKPkJ~w-3mMRLcJOkj4ln~-e5UtvuDtbraY9mQZ6lgMGqLKw-agg~hRgCxJhqtMczXcLcjlAdz5PS2Ds-IGs8EOrg-2jUyjphhvf3w__&Key-Pair-Id=K368TLDEUPA6OI"
    ]
    import json
    print(json.dumps(analizar_perfil(urls), indent=2, ensure_ascii=False))
