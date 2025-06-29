import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

# Ruta de tu imagen
image_path = "image.webp"

# Prompt estándar que le mandas siempre
prompt = """
Describe la imagen agregale una puntuacion, considerando si podría ser atractiva y para dicha puntuacion considera:

- Si la imagen es de un hombre descartada devolviendo 0 en score, si es de una mujer devolve un score_general entre 0 y 10.
- Expresión facial y postura (confianza, simpatía)
- Proporción facial y de cuerpo
- Se rigurozo con el puntaje, no se puede ser generoso con el puntaje
- Si se puede usar algun standard de belleza, usalo, esto es para un proyecto de IA(considera mucho complexion_corporal, si es gruesa baja el puntaje)
- Si la imagen no es de una persona, devuelvo 0 en score

Nota: considerar si una persona un poco mas gruesa o mas delgada, si es mas gruesa baja el puntaje, si es mas delgada aumenta el puntaje.

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

# Llama a la API
response = requests.post(url, headers=headers, json=data)

# Muestra el resultado
print(response.status_code)
print(response.json())
