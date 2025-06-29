from openai import analizar_imagen_openai

resultado = analizar_imagen_openai("002.webp")
if resultado:
    print("✅ Resultado:")
    print(resultado)
else:
    print("❌ No se obtuvo respuesta válida.")
