import google.generativeai as genai
import os

# --- IMPORTANTE: PON AQUÍ TU CLAVE DE API ---
# Intenta obtenerla de la variable de entorno, si no, ponla directamente.
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCMnN7EHR5KhE-g_qB44aAQpjP8PCNRVhw") 
# -----------------------------------------

print("Configurando la API de Gemini...")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    print("¡Configuración exitosa! Enviando consulta de prueba...")
    
    response = model.generate_content("Hola, mundo")
    
    print("\n✅ ¡Conexión exitosa!")
    print("Respuesta de Gemini:")
    print(response.text)

except Exception as e:
    print("\n❌ ¡Ocurrió un error!")
    print("El error detallado es:")
    print(e)