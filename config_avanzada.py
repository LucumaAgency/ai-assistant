# Configuración avanzada para optimización adicional

CONFIGURACION_MEMORIA = {
    # Límites de memoria
    "max_mensajes_recientes": 10,      # Reducir a 5 para respuestas más rápidas
    "max_mensajes_importantes": 20,    # Reducir a 10 si hay problemas
    "max_tokens_resumen": 500,         # Límite para cada resumen
    
    # Auto-limpieza
    "dias_para_archivar": 7,           # Archivar conversaciones de +7 días
    "max_resumenes_acumulados": 5,     # Máximo de resúmenes históricos
    
    # Modelos por tarea
    "modelo_conversacion": "gpt-4",    # Puedes cambiar a gpt-3.5-turbo para ahorrar
    "modelo_resumenes": "gpt-3.5-turbo", # Modelo económico para resúmenes
    
    # Triggers de mantenimiento
    "mensajes_antes_resumir": 20,      # Crear resumen cada 20 mensajes
    "iniciar_sesion_automatica": True, # Nueva sesión cada día
}

# Sistema de monitoreo
class MonitoreoRendimiento:
    def __init__(self):
        self.tiempos_respuesta = []
        self.tokens_usados = []
        
    def registrar_interaccion(self, tiempo, tokens):
        self.tiempos_respuesta.append(tiempo)
        self.tokens_usados.append(tokens)
        
        # Alertar si hay degradación
        if len(self.tiempos_respuesta) > 10:
            promedio_reciente = sum(self.tiempos_respuesta[-10:]) / 10
            if promedio_reciente > 5.0:  # Más de 5 segundos
                return "⚠️ El sistema está tardando más de lo normal. Considera iniciar nueva sesión."
        return None

# Función para mantenimiento automático
def mantenimiento_automatico(memoria):
    """Ejecutar diariamente para mantener el sistema óptimo"""
    import glob
    from datetime import datetime, timedelta
    
    # 1. Archivar conversaciones antiguas
    archivos_antiguos = []
    for archivo in glob.glob("session_archive_*.json"):
        fecha_archivo = os.path.getmtime(archivo)
        if datetime.fromtimestamp(fecha_archivo) < datetime.now() - timedelta(days=30):
            archivos_antiguos.append(archivo)
    
    # 2. Comprimir archivos antiguos
    if archivos_antiguos:
        import zipfile
        with zipfile.ZipFile(f"archivo_historico_{datetime.now().strftime('%Y%m')}.zip", 'w') as zf:
            for archivo in archivos_antiguos:
                zf.write(archivo)
                os.remove(archivo)
    
    # 3. Optimizar memoria actual
    if len(memoria.summary) > CONFIGURACION_MEMORIA["max_tokens_resumen"] * 5:
        # Resumir el resumen si es muy largo
        memoria.summary = crear_super_resumen(memoria.summary)
    
    return f"Mantenimiento completado. Archivos comprimidos: {len(archivos_antiguos)}"

# Modo económico para uso intensivo
def modo_economico(client, pregunta):
    """Usa GPT-3.5 para preguntas simples y ahorra costos"""
    palabras_clave_simples = ['qué hora', 'cómo estás', 'hola', 'adiós', 'gracias']
    
    if any(palabra in pregunta.lower() for palabra in palabras_clave_simples):
        # Usar modelo más barato para preguntas simples
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pregunta}],
            max_tokens=150
        )
        return response.choices[0].message.content
    
    return None  # Usar GPT-4 para preguntas complejas