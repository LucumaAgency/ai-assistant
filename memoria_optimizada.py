import json
import os
from datetime import datetime, timedelta
from openai import OpenAI

class MemoriaOptimizada:
    def __init__(self, client, max_recent_messages=10, max_important_messages=20):
        self.client = client
        self.max_recent = max_recent_messages
        self.max_important = max_important_messages
        self.memory_file = "optimized_memory.json"
        self.load_memory()
    
    def load_memory(self):
        """Carga la memoria desde archivo"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.summary = data.get('summary', '')
                self.important_messages = data.get('important', [])
                self.recent_messages = data.get('recent', [])
        else:
            self.summary = ""
            self.important_messages = []
            self.recent_messages = []
    
    def save_memory(self):
        """Guarda la memoria optimizada"""
        data = {
            'summary': self.summary,
            'important': self.important_messages[-self.max_important:],
            'recent': self.recent_messages[-self.max_recent:]
        }
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_message(self, role, content):
        """Agrega un mensaje y determina si es importante"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        # Agregar a mensajes recientes
        self.recent_messages.append(message)
        
        # Verificar si es importante
        important_keywords = [
            'importante', 'recordar', 'no olvides', 'guarda esto',
            'mi nombre es', 'vivo en', 'trabajo en', 'prefiero'
        ]
        
        if any(keyword in content.lower() for keyword in important_keywords):
            self.important_messages.append(message)
        
        # Si hay demasiados mensajes recientes, crear resumen
        if len(self.recent_messages) > self.max_recent * 2:
            self.create_summary()
        
        self.save_memory()
    
    def create_summary(self):
        """Crea un resumen de mensajes antiguos"""
        # Tomar mensajes que serán archivados
        to_summarize = self.recent_messages[:-self.max_recent]
        
        if to_summarize:
            # Preparar prompt para resumen
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in to_summarize])
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Usar modelo más económico para resúmenes
                messages=[
                    {"role": "system", "content": "Resume los puntos clave de esta conversación en máximo 200 palabras:"},
                    {"role": "user", "content": conversation}
                ],
                max_tokens=300
            )
            
            new_summary = response.choices[0].message.content
            
            # Combinar con resumen anterior si existe
            if self.summary:
                self.summary = f"{self.summary}\n\n---\n\n{new_summary}"
            else:
                self.summary = new_summary
            
            # Mantener solo mensajes recientes
            self.recent_messages = self.recent_messages[-self.max_recent:]
    
    def get_context_for_ai(self):
        """Prepara el contexto optimizado para enviar a la IA"""
        messages = []
        
        # Agregar resumen si existe
        if self.summary:
            messages.append({
                "role": "system",
                "content": f"Contexto histórico resumido:\n{self.summary}"
            })
        
        # Agregar mensajes importantes
        if self.important_messages:
            important_summary = "\n".join([
                f"- {msg['content']}" for msg in self.important_messages[-5:]
            ])
            messages.append({
                "role": "system",
                "content": f"Información importante a recordar:\n{important_summary}"
            })
        
        # Agregar mensajes recientes
        for msg in self.recent_messages[-self.max_recent:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        return messages
    
    def start_new_session(self):
        """Inicia una nueva sesión manteniendo solo lo esencial"""
        # Archivar sesión actual
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = f"session_archive_{timestamp}.json"
        
        # Guardar archivo completo antes de limpiar
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                data = json.load(f)
            with open(archive_file, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Crear resumen final de la sesión
        if self.recent_messages:
            self.create_summary()
        
        # Limpiar mensajes recientes pero mantener importantes y resumen
        self.recent_messages = []
        self.save_memory()
        
        print(f"Nueva sesión iniciada. Sesión anterior archivada en: {archive_file}")


# Ejemplo de uso integrado con tu programa existente
def integrate_with_existing_program(client):
    """Ejemplo de cómo integrar con tu programa actual"""
    
    # Crear instancia de memoria optimizada
    memoria = MemoriaOptimizada(client)
    
    # En vez de usar add_to_memory(), usar:
    # memoria.add_message("user", transcription_text)
    
    # Para obtener contexto para GPT-4:
    # messages = memoria.get_context_for_ai()
    
    # Para iniciar nueva sesión (puede ser un botón en la UI):
    # memoria.start_new_session()
    
    return memoria