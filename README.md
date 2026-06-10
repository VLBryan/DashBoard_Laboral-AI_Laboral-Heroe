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
### Variables de entorno

Copia `.env.example` a `.env` y completa tus credenciales. No lo subas a GitHub.

```bash
cp .env.example .env
```

```bash
# .env
MONGO_URI=mongodb+srv://usuario:password@cluster-host/db_name?retryWrites=true&w=majority&appName=app-name
LABORAL_DB=nombre_de_tu_db
CACHE_DIR=./cache   
```

`config.py` carga estas variables (vía `python-dotenv`) y las expone como
`DB_NAME`, `MONGO_URI` y `CACHE_DIR`. Alternativamente, si existe un archivo
`config_private.py` en la raíz con esas mismas variables, tiene prioridad sobre
el `.env`.

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

## Estructura del proyecto

```
.
├── app.py                # Entrypoint de Streamlit (UI)
├── config.py             # Carga de configuración (.env / config_private.py)
├── src/
│   ├── data_loader.py     # ETL: Mongo -> df_master / df_user_skills + cache Parquet
│   ├── kpi_calculator.py  # KPIs globales
│   ├── kpi_by_location.py # KPIs segmentados por ubicación
│   └── viz_factory.py     # Gráficos Plotly/Altair
├── scripts/
│   └── run_etl.py          # Refresca el cache Parquet sin levantar Streamlit
├── tests/                  # Tests unitarios (pytest)
└── cache/                   # Cache local en Parquet (no versionado)
```

## ETL standalone

Para refrescar el cache de datos (`cache/df_master.parquet`,
`cache/df_user_skills.parquet`) sin levantar el dashboard:

```bash
python scripts/run_etl.py
```

## Tests

Instala las dependencias de desarrollo y corre la suite con `pytest`:

```bash
pip install -r requirements-dev.txt
pytest
```

## Autor
**Bryan Villasante López**
Estudiante de Big Data y Ciencia de Datos en TECSUP · Pasante en Laboral.AI