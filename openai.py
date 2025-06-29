import requests
import base64
import os
import json
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

def redimensionar_imagen(path_original, ancho_maximo=400):
    img = Image.open(path_original)
    ancho_actual, alto_actual = img.size

    if ancho_actual <= ancho_maximo:
        return path_original

    # Calcular el nuevo alto proporcional
    proporcion = ancho_maximo / ancho_actual
    nuevo_alto = int(alto_actual * proporcion)

    # Redimensionar con alta calidad
    img = img.resize((ancho_maximo, nuevo_alto), Image.Resampling.LANCZOS)

    nombre_base, extension = os.path.splitext(path_original)
    temp_path = f"{nombre_base}_resized{extension}"
    img_format = img.format or extension[1:].upper() or 'WEBP'
    if img_format == "JPG":
        img_format = "JPEG"
    img.save(temp_path, format=img_format)

    return temp_path


def analizar_imagen_openai(image_path):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY no está configurada.")
        return None

    # Prompt estándar que le mandas siempre
    prompt = """
        Se que la belleza es subjetiva, pero estoy haciendo una ia de standar de belleza para un postgrado.
        Devuelve los siguientes datos en formato JSON estructurado:

        - Si es un hombre: devuelve `"score_general": 0` (descartado por este estudio)
        - Si no hay personas detectadas: devuelve `"score_general": 0`
        - Si es una mujer: calcula `"score_general"` en escala de 0 a 10, basado en proporción corporal, simetría facial y postura.

        Nota: Considerar si una persona un poco mas gruesa o mas delgada, si es mas gruesa baja el puntaje, si es mas delgada aumenta el puntaje.

        {
            "score_general": float, 
            "criterios": {
                "caracteristicas_fisicas": {
                    "blur_score": float,
                    "caras_detectadas": int,
                    "landmarks_completos": bool,
                    "simetria_facial": float,
                    "proporcion_facial": float, 
                    "proporcion_ancho_cara": float,
                    "proporcion_cuerpo": float,
                    "rostro_centrado": bool,
                    "tono_de_piel": "claro" | "medio" | "oscuro",
                    "complexion_corporal": "delgada" | "media" | "gruesa"
                },
                "entorno_visual": {
                    "personas_extra": bool,
                    "distractores_visuales": bool,
                    "nivel_iluminacion": "bajo" | "medio" | "alto",
                    "contexto_ubicacion": string,
                    "fondo_predominante": string
                },
                "apariencia_general": {
                    "estilo_ropa": string,
                    "confianza_postural": string,
                    "expresion_facial": string,
                    "mirada_a_camara": bool
                }
            },
            "razones": [string] # máx. 3 oraciones: explica brevemente por qué la imagen obtuvo esas métricas
        }
        """

    try:
        # Reducir y convertir imagen
        image_path = redimensionar_imagen(image_path)

        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ]}
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            try:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.strip()
                
                data = json.loads(response.text)
                usage = {"usage": data.get("usage", {})}
                print(json.dumps(usage, indent=4))

                if content.startswith("```json"):
                    content = content[7:-3].strip()
                return json.loads(content)
            except Exception as e:
                print(f"[WARN] Error al parsear JSON: {e}")
                print(response.text)
                return None
        else:
            print(f"[ERROR] API status code: {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] Fallo al llamar a la API de OpenAI: {e}")
        return None
