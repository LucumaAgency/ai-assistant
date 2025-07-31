import json
import os
import datetime
import sounddevice as sd
import wavio
import numpy as np
import threading
import speech_recognition as sr
from openai import OpenAI
from tkinter import Tk, Button, Label, Frame, Text, Scrollbar, END, messagebox, StringVar, OptionMenu
from memoria_optimizada import MemoriaOptimizada
from dotenv import load_dotenv
import time

# Cargar variables de entorno desde archivo .env
load_dotenv()

# Verificar que la API key esté configurada
api_key = os.getenv('OPENAI_API_KEY')
if not api_key or api_key == 'tu-api-key-aqui':
    messagebox.showerror(
        "Error de Configuración",
        "Por favor configura tu OPENAI_API_KEY en el archivo .env\n\n"
        "1. Copia .env.example a .env\n"
        "2. Agrega tu API key de OpenAI"
    )
    exit(1)

# Inicializar el cliente de OpenAI con la API key del entorno
client = OpenAI(api_key=api_key)

# Configuración desde variables de entorno
max_recent = int(os.getenv('MAX_RECENT_MESSAGES', '5'))  # Reducido de 10 a 5
max_important = int(os.getenv('MAX_IMPORTANT_MESSAGES', '10'))  # Reducido de 20 a 10

# Variables para la grabación
recording = False
audio_file_name = ""
frames = []

# Inicializar Speech Recognition
recognizer = sr.Recognizer()

# Inicializar memoria optimizada con configuración del entorno
memoria = MemoriaOptimizada(client, max_recent_messages=max_recent, max_important_messages=max_important)

# Estadísticas de uso
stats = {
    'total_cost': 0.0,
    'whisper_saved': 0.0,
    'tokens_used': 0,
    'gpt4_calls': 0,
    'gpt35_calls': 0
}

def detect_complexity(text):
    """Detecta si una pregunta requiere GPT-4 o puede usar GPT-3.5"""
    # Palabras clave que indican preguntas simples
    simple_keywords = [
        'hola', 'buenos días', 'buenas tardes', 'adiós', 
        'gracias', 'por favor', 'cómo estás', 'qué hora',
        'qué día', 'cuánto es', 'dime un chiste'
    ]
    
    # Palabras clave que indican preguntas complejas
    complex_keywords = [
        'código', 'programa', 'debug', 'error', 'implementa',
        'analiza', 'optimiza', 'arquitectura', 'diseña',
        'explica en detalle', 'compara', 'estrategia'
    ]
    
    text_lower = text.lower()
    
    # Si es muy corto, probablemente es simple
    if len(text.split()) < 5:
        return 'simple'
    
    # Verificar palabras clave complejas
    for keyword in complex_keywords:
        if keyword in text_lower:
            return 'complex'
    
    # Verificar palabras clave simples
    for keyword in simple_keywords:
        if keyword in text_lower:
            return 'simple'
    
    # Por defecto, usar el modelo económico
    return 'medium'

def save_recording():
    """Procesa el audio grabado y lo guarda"""
    global audio_file_name, frames
    sample_rate = 44100
    if frames:
        full_recording = np.concatenate(frames, axis=0)
        wavio.write(audio_file_name, full_recording, sample_rate, sampwidth=2)
        status_label.config(text=f"Procesando audio...")
        frames = []
        
        # Procesar con Google Speech Recognition
        process_audio_with_google(audio_file_name)
    else:
        status_label.config(text="No se grabó ningún audio.")

def process_audio_with_google(file_path):
    """Procesa el audio usando Google Speech Recognition (GRATIS)"""
    try:
        start_time = time.time()
        
        # Cargar el archivo de audio
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        
        status_label.config(text="Transcribiendo con Google...")
        
        # Transcribir usando Google (GRATIS)
        try:
            transcription_text = recognizer.recognize_google(audio, language="es-ES")
            transcription_time = time.time() - start_time
            
            # Calcular ahorro vs Whisper
            audio_duration = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
            whisper_cost = (audio_duration / 60) * 0.006  # $0.006 por minuto
            stats['whisper_saved'] += whisper_cost
            
            # Mostrar transcripción
            conversation_text.insert(END, f"\n👤 Usuario: {transcription_text}\n", "user")
            conversation_text.insert(END, f"   [Google Speech - {transcription_time:.1f}s - Ahorrado: ${whisper_cost:.4f}]\n", "system")
            conversation_text.see(END)
            
        except sr.UnknownValueError:
            # Si Google no entiende, intentar con otro servicio
            status_label.config(text="No se pudo entender el audio, intenta de nuevo")
            return
        except sr.RequestError as e:
            status_label.config(text=f"Error con Google Speech: {e}")
            return
        
        # Agregar a memoria
        memoria.add_message("user", transcription_text)
        
        # Detectar complejidad y elegir modelo
        complexity = detect_complexity(transcription_text)
        if complexity == 'simple':
            model = 'gpt-3.5-turbo'
            stats['gpt35_calls'] += 1
            model_info = "GPT-3.5"
        elif complexity == 'complex':
            model = 'gpt-4'
            stats['gpt4_calls'] += 1
            model_info = "GPT-4"
        else:
            model = 'gpt-3.5-turbo'  # Por defecto usar el económico
            stats['gpt35_calls'] += 1
            model_info = "GPT-3.5"
        
        status_label.config(text=f"Procesando con {model_info}...")
        
        # Obtener contexto optimizado
        messages = memoria.get_context_for_ai()
        
        # Calcular tokens aproximados
        context_tokens = sum(len(msg['content'].split()) * 1.3 for msg in messages)
        
        # Generar respuesta
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=300  # Limitar respuesta para ahorrar
        )
        
        assistant_response = response.choices[0].message.content
        
        # Calcular costo
        total_tokens = response.usage.total_tokens
        stats['tokens_used'] += total_tokens
        
        if model == 'gpt-4':
            cost = (response.usage.prompt_tokens * 0.03 + response.usage.completion_tokens * 0.06) / 1000
        else:  # gpt-3.5-turbo
            cost = (response.usage.prompt_tokens * 0.0015 + response.usage.completion_tokens * 0.002) / 1000
        
        stats['total_cost'] += cost
        
        # Agregar respuesta a memoria
        memoria.add_message("assistant", assistant_response)
        
        # Mostrar respuesta
        conversation_text.insert(END, f"\n🤖 Asistente ({model_info}): {assistant_response}\n", "assistant")
        conversation_text.insert(END, f"   [Tokens: {total_tokens} - Costo: ${cost:.4f}]\n", "system")
        conversation_text.see(END)
        
        # Guardar respuesta
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H-%M-%S")
        file_name = f"respuesta_{formatted_time}.md"
        with open(file_name, "w", encoding='utf-8') as file:
            file.write(f"# Respuesta del Asistente\n\n")
            file.write(f"**Fecha:** {formatted_time}\n")
            file.write(f"**Modelo:** {model}\n")
            file.write(f"**Tokens:** {total_tokens}\n")
            file.write(f"**Costo:** ${cost:.4f}\n\n")
            file.write(f"**Pregunta:** {transcription_text}\n\n")
            file.write(f"**Respuesta:**\n\n{assistant_response}")
        
        # Actualizar estadísticas
        update_stats()
        status_label.config(text="Respuesta completada")
        
    except Exception as e:
        status_label.config(text=f"Error: {str(e)}")
        print(f"Error procesando audio: {e}")

def record_audio():
    """Graba audio en segundo plano"""
    global recording, frames
    sample_rate = 44100
    channels = 1
    duration = 1

    while recording:
        fragment = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=channels)
        sd.wait()
        frames.append(fragment)

def toggle_recording():
    """Inicia/detiene la grabación"""
    global recording, audio_file_name
    if recording:
        recording = False
        record_button.config(text="🎤 Grabar", bg="#4CAF50")
        save_recording()
    else:
        recording = True
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_file_name = f"audio_{timestamp}.wav"
        record_button.config(text="⏹️ Detener", bg="#f44336")
        status_label.config(text="Grabando...")
        threading.Thread(target=record_audio).start()

def start_new_session():
    """Inicia una nueva sesión"""
    memoria.start_new_session()
    conversation_text.delete(1.0, END)
    conversation_text.insert(END, "🔄 Nueva sesión iniciada\n\n", "system")
    status_label.config(text="Nueva sesión iniciada")
    update_stats()

def update_stats():
    """Actualiza las estadísticas mostradas"""
    total_messages = len(memoria.recent_messages) + len(memoria.important_messages)
    stats_label.config(
        text=f"📊 Mensajes: {total_messages} | "
        f"GPT-4: {stats['gpt4_calls']} | GPT-3.5: {stats['gpt35_calls']} | "
        f"Costo total: ${stats['total_cost']:.2f} | "
        f"Ahorrado en Whisper: ${stats['whisper_saved']:.2f}"
    )

def show_savings():
    """Muestra un resumen de ahorros"""
    total_saved = stats['whisper_saved']
    total_interactions = stats['gpt4_calls'] + stats['gpt35_calls']
    
    if total_interactions > 0:
        avg_cost = stats['total_cost'] / total_interactions
        message = f"""💰 Resumen de Ahorros:

🎤 Ahorrado en transcripción: ${stats['whisper_saved']:.2f}
📝 Total de interacciones: {total_interactions}
💵 Costo promedio por consulta: ${avg_cost:.3f}
💸 Costo total: ${stats['total_cost']:.2f}

🚀 Optimizaciones aplicadas:
✓ Google Speech en vez de Whisper
✓ GPT-3.5 para consultas simples ({stats['gpt35_calls']} veces)
✓ GPT-4 solo cuando necesario ({stats['gpt4_calls']} veces)
✓ Límite de tokens por respuesta
✓ Contexto reducido (máx {max_recent} mensajes)"""
    else:
        message = "📊 Aún no hay estadísticas. ¡Haz tu primera consulta!"
    
    messagebox.showinfo("Resumen de Ahorros", message)

# Configuración de la interfaz gráfica
root = Tk()
root.title("Asistente de Voz IA v4 - Optimizado con Google Speech")
root.geometry("900x700")
root.configure(bg="#f0f0f0")

# Frame principal
main_frame = Frame(root, bg="#f0f0f0")
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

# Frame superior con botones
button_frame = Frame(main_frame, bg="#f0f0f0")
button_frame.pack(fill="x", pady=(0, 10))

# Botón de grabación
record_button = Button(
    button_frame, 
    text="🎤 Grabar", 
    command=toggle_recording, 
    width=12, 
    height=2,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3
)
record_button.pack(side="left", padx=5)

# Botón de nueva sesión
session_button = Button(
    button_frame,
    text="🔄 Nueva Sesión",
    command=start_new_session,
    width=12,
    height=2,
    bg="#2196F3",
    fg="white",
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3
)
session_button.pack(side="left", padx=5)

# Botón de estadísticas
stats_button = Button(
    button_frame,
    text="💰 Ver Ahorros",
    command=show_savings,
    width=12,
    height=2,
    bg="#FF9800",
    fg="white",
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3
)
stats_button.pack(side="left", padx=5)

# Área de conversación
conversation_frame = Frame(main_frame, bg="#f0f0f0")
conversation_frame.pack(fill="both", expand=True, pady=10)

# Scrollbar
scrollbar = Scrollbar(conversation_frame)
scrollbar.pack(side="right", fill="y")

# Área de texto
conversation_text = Text(
    conversation_frame,
    wrap="word",
    yscrollcommand=scrollbar.set,
    font=("Arial", 11),
    bg="white",
    fg="#333333",
    padx=10,
    pady=10
)
conversation_text.pack(side="left", fill="both", expand=True)
scrollbar.config(command=conversation_text.yview)

# Tags para diferentes tipos de mensajes
conversation_text.tag_config("user", foreground="#0066cc", font=("Arial", 11, "bold"))
conversation_text.tag_config("assistant", foreground="#009900", font=("Arial", 11))
conversation_text.tag_config("system", foreground="#666666", font=("Arial", 9, "italic"))

# Etiqueta de estado
status_label = Label(
    main_frame, 
    text="Presiona 'Grabar' para iniciar",
    bg="#f0f0f0",
    fg="#666666",
    font=("Arial", 10)
)
status_label.pack(pady=5)

# Etiqueta de estadísticas
stats_label = Label(
    main_frame,
    text="📊 Esperando primera consulta...",
    bg="#f0f0f0",
    fg="#666666",
    font=("Arial", 9)
)
stats_label.pack(pady=2)

# Mensaje de bienvenida
conversation_text.insert(END, "🤖 Asistente de Voz IA v4 - Optimizado\n", "system")
conversation_text.insert(END, "✨ Ahora con Google Speech Recognition (GRATIS)\n", "system")
conversation_text.insert(END, "💡 Detección automática de complejidad\n", "system")
conversation_text.insert(END, "💰 Uso inteligente de GPT-3.5 vs GPT-4\n\n", "system")

# Ejecutar la interfaz
root.mainloop()