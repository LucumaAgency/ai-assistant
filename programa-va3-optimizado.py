import openai
import json
import os
import datetime
import sounddevice as sd
import wavio
import numpy as np
import threading
from openai import OpenAI
from tkinter import Tk, Button, Label, Frame, Text, Scrollbar, END, messagebox
from memoria_optimizada import MemoriaOptimizada
from dotenv import load_dotenv

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

# Variables para la grabación
recording = False
audio_file_name = ""
frames = []  # Para almacenar los fragmentos de audio

# Configuración desde variables de entorno
max_recent = int(os.getenv('MAX_RECENT_MESSAGES', '10'))
max_important = int(os.getenv('MAX_IMPORTANT_MESSAGES', '20'))
model_name = os.getenv('OPENAI_MODEL', 'gpt-4')

# Inicializar memoria optimizada con configuración del entorno
memoria = MemoriaOptimizada(client, max_recent_messages=max_recent, max_important_messages=max_important)

# Función para procesar el audio grabado y guardar
def save_recording():
    global audio_file_name, frames
    sample_rate = 44100
    if frames:
        # Concatenar todos los fragmentos de grabación en un solo array de numpy
        full_recording = np.concatenate(frames, axis=0)
        # Guardar la grabación como un archivo .wav
        wavio.write(audio_file_name, full_recording, sample_rate, sampwidth=2)
        status_label.config(text=f"Grabación guardada: {audio_file_name}")
        frames = []  # Limpiar la lista de fragmentos
    else:
        status_label.config(text="No se grabó ningún audio.")

# Función para grabar audio en segundo plano
def record_audio():
    global recording, frames
    sample_rate = 44100
    channels = 1
    duration = 1  # Duración de cada fragmento de grabación

    while recording:
        # Graba un fragmento corto (1 segundo)
        fragment = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=channels)
        sd.wait()
        frames.append(fragment)

# Función para iniciar/detener la grabación
def toggle_recording():
    global recording, audio_file_name
    if recording:
        recording = False
        record_button.config(text="🎤 Grabar", bg="#4CAF50")
        save_recording()
        process_audio_file(audio_file_name)
    else:
        recording = True
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_file_name = f"audio_{timestamp}.wav"
        record_button.config(text="⏹️ Detener", bg="#f44336")
        status_label.config(text="Grabando...")
        # Inicia un nuevo hilo para grabar en segundo plano
        threading.Thread(target=record_audio).start()

# Función para procesar el archivo de audio
def process_audio_file(file_path):
    if os.path.exists(file_path):
        try:
            status_label.config(text="Transcribiendo audio...")
            
            with open(file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            transcription_text = transcription.text
            
            # Mostrar transcripción en el área de texto
            conversation_text.insert(END, f"\n👤 Usuario: {transcription_text}\n", "user")
            conversation_text.see(END)
            
            # Agregar a memoria optimizada
            memoria.add_message("user", transcription_text)
            
            status_label.config(text="Procesando respuesta...")
            
            # Obtener contexto optimizado
            messages = memoria.get_context_for_ai()
            
            # Generar respuesta con modelo configurado
            response = client.chat.completions.create(
                model=model_name,
                messages=messages
            )

            assistant_response = response.choices[0].message.content
            
            # Agregar respuesta a memoria
            memoria.add_message("assistant", assistant_response)
            
            # Mostrar respuesta en el área de texto
            conversation_text.insert(END, f"\n🤖 Asistente: {assistant_response}\n", "assistant")
            conversation_text.see(END)
            
            # Guardar la respuesta en un archivo Markdown
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d %H-%M-%S")
            file_name = f"respuesta_{formatted_time}.md"
            with open(file_name, "w", encoding='utf-8') as file:
                file.write(f"# Respuesta del Asistente\n\n")
                file.write(f"**Fecha:** {formatted_time}\n\n")
                file.write(f"**Pregunta:** {transcription_text}\n\n")
                file.write(f"**Respuesta:**\n\n")
                file.write(assistant_response)

            status_label.config(text=f"Respuesta guardada en {file_name}")
            
            # Actualizar estadísticas
            update_stats()
            
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}")
            print(f"Error procesando audio: {e}")
    else:
        status_label.config(text=f"No se encontró el archivo: {file_path}")

# Función para iniciar nueva sesión
def start_new_session():
    memoria.start_new_session()
    conversation_text.delete(1.0, END)
    conversation_text.insert(END, "🔄 Nueva sesión iniciada\n\n", "system")
    status_label.config(text="Nueva sesión iniciada - Historial archivado")
    update_stats()

# Función para actualizar estadísticas
def update_stats():
    total_messages = len(memoria.recent_messages) + len(memoria.important_messages)
    stats_label.config(text=f"📊 Mensajes recientes: {len(memoria.recent_messages)} | Importantes: {len(memoria.important_messages)}")

# Configuración de la interfaz gráfica mejorada
root = Tk()
root.title("Asistente de Voz con IA - Versión Optimizada")
root.geometry("800x600")
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
    width=15, 
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
    width=15,
    height=2,
    bg="#2196F3",
    fg="white",
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3
)
session_button.pack(side="left", padx=5)

# Área de conversación
conversation_frame = Frame(main_frame, bg="#f0f0f0")
conversation_frame.pack(fill="both", expand=True, pady=10)

# Scrollbar
scrollbar = Scrollbar(conversation_frame)
scrollbar.pack(side="right", fill="y")

# Área de texto para mostrar conversación
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

# Configurar tags para diferentes tipos de mensajes
conversation_text.tag_config("user", foreground="#0066cc")
conversation_text.tag_config("assistant", foreground="#009900")
conversation_text.tag_config("system", foreground="#666666", font=("Arial", 10, "italic"))

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
    text="📊 Mensajes recientes: 0 | Importantes: 0",
    bg="#f0f0f0",
    fg="#666666",
    font=("Arial", 9)
)
stats_label.pack(pady=2)

# Inicializar estadísticas
update_stats()

# Mensaje de bienvenida
conversation_text.insert(END, "🤖 Asistente de Voz con IA - Versión Optimizada\n", "system")
conversation_text.insert(END, "Sistema de memoria inteligente activado\n\n", "system")

# Ejecutar la interfaz gráfica
root.mainloop()