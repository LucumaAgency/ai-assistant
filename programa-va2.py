import openai
import json
import os
import datetime
import sounddevice as sd
import wavio
import numpy as np
import threading
from openai import OpenAI
from tkinter import Tk, Button, Label

# Inicializar el cliente de OpenAI con tu API key
client = OpenAI(api_key='sk-8NoaZ5IBFkpAdKqHG-7nbWgo0LdkUcssudVU5d4wyFT3BlbkFJxx5-Pax5wcOlI8TiNKEjIwLAc9mvIhqA6MblzRdfdfCs4A')

# Nombre del archivo JSON para guardar la memoria completa
memory_file = "full_memory.json"

# Variables para la grabación
recording = False
audio_file_name = ""
frames = []  # Para almacenar los fragmentos de audio

# Función para cargar la memoria completa desde el archivo JSON
def load_full_memory():
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                return data
            except json.JSONDecodeError:
                # Si el archivo está vacío o dañado, retorna una lista vacía
                return []
    return []

# Función para guardar la memoria completa en el archivo JSON
def save_full_memory(memory):
    with open(memory_file, 'w', encoding='utf-8') as file:
        json.dump(memory, file, ensure_ascii=False, indent=4)

# Cargar la memoria existente
memory = load_full_memory()

# Función para agregar nueva interacción a la memoria
def add_to_memory(role, content):
    memory.append({"role": role, "content": content})
    save_full_memory(memory)

# Función para contar tokens de forma más precisa
def count_tokens(text):
    return len(text.split())

# Función para recortar la memoria de manera más estricta si supera el límite de tokens
def trim_memory(memory, max_length=8000):
    total_tokens = sum(count_tokens(msg['content']) for msg in memory)
    while total_tokens > max_length and memory:
        memory.pop(0)  # Elimina la interacción más antigua
        total_tokens = sum(count_tokens(msg['content']) for msg in memory)
    return memory

# Función para procesar el audio grabado y guardar
def save_recording():
    global audio_file_name, frames
    sample_rate = 44100
    if frames:
        # Concatenar todos los fragmentos de grabación en un solo array de numpy
        full_recording = np.concatenate(frames, axis=0)
        # Guardar la grabación como un archivo .wav
        wavio.write(audio_file_name, full_recording, sample_rate, sampwidth=2)
        print(f"Grabación guardada en {audio_file_name}")
        frames = []  # Limpiar la lista de fragmentos
    else:
        print("No se grabó ningún audio.")

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
        record_button.config(text="Grabar")
        save_recording()
        process_audio_file(audio_file_name)
    else:
        recording = True
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_file_name = f"audio_{timestamp}.wav"
        record_button.config(text="Detener")
        # Inicia un nuevo hilo para grabar en segundo plano
        threading.Thread(target=record_audio).start()

# Función para detectar el último archivo de audio grabado
def get_latest_audio_file(directory='.'):
    audio_files = [f for f in os.listdir(directory) if f.endswith(".wav")]
    if not audio_files:
        return None
    latest_file = max(audio_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return latest_file

# Función para procesar el archivo de audio
def process_audio_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        transcription_text = transcription.text
        print(f"Transcripción del audio: {transcription_text}")
        add_to_memory("user", transcription_text)

        # Recortar la memoria si es necesario antes de enviar la solicitud
        trimmed_memory = trim_memory(memory)

        # Asegurarse de que la memoria recortada cumpla con el límite de tokens
        response = client.chat.completions.create(
            model="gpt-4",
            messages=trimmed_memory
        )

        assistant_response = response.choices[0].message.content
        add_to_memory("assistant", assistant_response)

        # Guardar la respuesta en un archivo Markdown
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H-%M-%S")
        file_name = f"respuesta_{formatted_time}.md"
        with open(file_name, "w", encoding='utf-8') as file:
            file.write(f"# Respuesta del Asistente\n\n")
            file.write(f"**Fecha:** {formatted_time}\n\n")
            file.write(f"**Respuesta:**\n\n")
            file.write(assistant_response)

        print(f"La respuesta se ha guardado en {file_name}")
    else:
        print(f"No se encontró el archivo de audio en {file_path}")

# Configuración de la interfaz gráfica con tkinter
root = Tk()
root.title("Grabador de Voz con OpenAI")
root.geometry("300x200")

# Botón de grabación
record_button = Button(root, text="Grabar", command=toggle_recording, width=20, height=2)
record_button.pack(pady=20)

# Etiqueta de estado
status_label = Label(root, text="Presiona 'Grabar' para iniciar la grabación.")
status_label.pack(pady=20)

# Ejecutar la interfaz gráfica
root.mainloop()
