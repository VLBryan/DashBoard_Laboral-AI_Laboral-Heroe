# Dashboard Laboral.AI – Laboral Heroe

## Descripción del proyecto
Este repositorio contiene un **dashboard interactivo** desarrollado en **Python** con **Streamlit** y conectado a **MongoDB**.  
El dashboard centraliza y visualiza información de usuarios, CVs, empleabilidad y postulaciones para facilitar el análisis operativo y académico.  
Incluye KPIs, filtros dinámicos, vistas por usuario y agregados de habilidades que permiten explorar la base de usuarios y detectar patrones de empleabilidad.

**Funcionalidades principales**
- **KPIs**: usuarios activos, postulaciones, suma de postulaciones, porcentaje de Laboral Heroes, distribución de scores.  
- **Filtros**: rango de fechas, país, rango de score, estado Laboral Hero.  
- **Perfiles**: vista detallada por usuario con CV, top skills y métricas de empleabilidad.  
- **Agregados**: tablas y gráficos interactivos para análisis rápido.

## Motivos del desarrollo
**Por qué construimos esta solución**  
- **Costo y eficiencia**: alternativa ligera a herramientas comerciales que requieren licencias y recursos elevados.  
- **Despliegue web sencillo**: se puede ejecutar en servidores ligeros o plataformas cloud sin infraestructuras complejas.  
- **Transparencia y extensibilidad**: código abierto que facilita auditoría, integración con pipelines de ML y evolución del producto.  
- **Prototipado rápido**: cambios en visualizaciones y lógica de negocio se implementan con velocidad.

**Beneficios operativos**
- Acceso inmediato a métricas para decisiones de producto y operaciones.  
- Reutilización de datos para experimentos y modelos de recomendación.  
- Escalado progresivo desde prototipo a servicio productivo.

## Instalación y configuración
**Requisitos previos**
- Python 3.10 o superior  
- Git  
- Acceso a MongoDB con las colecciones necesarias

### Clonar el repositorio

```bash
git clone https://github.com/VLBryan/DashBoard_Laboral-AI_Laboral-Heroe.git
cd DashBoard_Laboral-AI_Laboral-Heroe
```

### Crear y activar entorno virtual

```bash
python -m venv venv
source venv/bin/activate   # Linux macOS
venv\Scripts\activate      # Windows
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```
### Archivo de configuración privada

Crea config_private.py en la raíz del proyecto. No lo subas a GitHub.

```bash
# config_private.py
# Aquí defines tus credenciales y configuraciones privadas

DB_NAME = "laboral_ai_db"
MONGO_URI = "mongodb://usuario:password@host:27017"
CACHE_DIR = "./cache"
```

## Uso y ejecución

Ejecutar localmente

```bash
source venv/bin/activate
streamlit run app.py
```

Abrir en el navegador:

```bash
http://localhost:8501
```

### Script de ejecución rápida

Crea run.sh para activar, ejecutar y desactivar automáticamente:

```bash
#!/bin/bash
source venv/bin/activate
streamlit run app.py
deactivate
```

Dar permisos y ejecutar:

```bash
chmod +x run.sh
./run.sh
```

## Autor
**Bryan Villasante López**
Estudiante de Big Data y Ciencia de Datos en TECSUP · Pasante en Laboral.AI