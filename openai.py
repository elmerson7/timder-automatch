import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

# Ruta de tu imagen
image_path = "test.jpg"

# Prompt estándar que le mandas siempre
prompt = """
Evalúa la belleza general del rostro humano y cuerpo tambien en esta imagen según los siguientes criterios:
- Simetría facial (escala 1 al 10, float)
- Proporción facial y de cuerpo
- Si la imagen es de un hombre descartada devolviendo 0 en score
- Expresión facial y postura
- Si tiene la piel mas oscura el puntaje se reduce
- Si tiene la piel mas clara el puntaje se aumenta
- Si tiene un cuerpo mas delgado el puntaje se aumenta
- Si tiene un cuerpo mas gordo el puntaje se reduce

Devuélveme una respuesta estructurada en JSON como este ejemplo:

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
      "rostro_centrado": bool
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
  "razones": [string]
}
"""

# Codifica la imagen a base64
with open(image_path, "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode("utf-8")

# API key (usa una variable de entorno en producción)
api_key = os.getenv("OPENAI_API_KEY")

# Payload para la API
url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "model": "gpt-4o",
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

# Llama a la API
response = requests.post(url, headers=headers, json=data)

# Muestra el resultado
print(response.status_code)
print(response.json())
