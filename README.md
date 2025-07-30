# Asistente de Voz con IA - Configuración

## 🚀 Instalación Rápida

### 1. Instalar Dependencias
```bash
pip install openai python-dotenv sounddevice wavio numpy
```

### 2. Configurar API Key de OpenAI

#### Opción A: Crear archivo .env (RECOMENDADO)
```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar el archivo .env y agregar tu API key
# OPENAI_API_KEY=sk-tu-api-key-real-aqui
```

#### Opción B: Variable de entorno del sistema
```bash
# Linux/Mac
export OPENAI_API_KEY="sk-tu-api-key-real-aqui"

# Windows (Command Prompt)
set OPENAI_API_KEY=sk-tu-api-key-real-aqui

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-tu-api-key-real-aqui"
```

### 3. Ejecutar el Programa
```bash
python programa-va3-optimizado.py
```

## 🔐 Seguridad

- **NUNCA** subas tu archivo `.env` a Git (ya está en .gitignore)
- **NUNCA** compartas tu API key
- La API key que estaba en el código original ya no es válida

## ⚙️ Variables de Configuración

Puedes personalizar estos valores en tu archivo `.env`:

```bash
# API Key de OpenAI (OBLIGATORIO)
OPENAI_API_KEY=tu-api-key-aqui

# Modelo de IA (opcional, default: gpt-4)
OPENAI_MODEL=gpt-4

# Límites de memoria (opcional)
MAX_RECENT_MESSAGES=10      # Mensajes recientes a mantener
MAX_IMPORTANT_MESSAGES=20   # Mensajes importantes a guardar
```

## 📁 Estructura de Archivos

```
ai-assistant/
├── .env                    # TU archivo con API key (NO compartir)
├── .env.example           # Ejemplo de configuración
├── .gitignore            # Archivos a ignorar en Git
├── programa-va3-optimizado.py  # Programa principal
├── memoria_optimizada.py  # Sistema de memoria inteligente
├── optimized_memory.json  # Memoria activa (se crea al usar)
└── session_archive_*.json # Archivos de sesiones anteriores
```

## 🆘 Solución de Problemas

### Error: "Por favor configura tu OPENAI_API_KEY"
1. Verifica que creaste el archivo `.env` (no `.env.example`)
2. Verifica que la API key está correcta y entre comillas
3. Reinicia el programa

### Error: "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### La API key no funciona
1. Verifica en https://platform.openai.com/api-keys
2. Genera una nueva API key si es necesario
3. Asegúrate de tener créditos en tu cuenta OpenAI