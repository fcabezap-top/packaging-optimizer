# Packaging Optimizer

**TFG — Grado en Ingeniería Informática (Desarrollo Web) — UOC 2026**  
Autor: Fernando Cabeza Pereira

Sistema software de **optimización tridimensional de packaging** para entornos logísticos. Dado un artículo con sus dimensiones físicas, el sistema calcula la configuración de embalaje más eficiente (caja interior + contenedor master), respetando restricciones de peso, orientación y reglas operativas configuradas por el gestor.

---

## Requisitos previos

- [Docker](https://www.docker.com/get-started) (v24+) con Docker Compose incluido
- Git

No se necesita ningún otro software instalado. Todo corre dentro de contenedores.

---

## Arranque rápido

```bash
git clone https://github.com/fcabezap-top/packaging-optimizer.git
cd packaging-optimizer
docker compose up --build
```

La primera vez tarda ~2-3 minutos en construir las imágenes. A partir de la segunda, simplemente:

```bash
docker compose up
```

Al arrancar, cada servicio ejecuta automáticamente un **seed** que carga datos de prueba si las colecciones están vacías (usuarios, productos, contenedores, reglas).

---

## URLs de acceso

| Servicio | URL |
|---|---|
| **Frontend (aplicación web)** | http://localhost:5173 |
| users-service API | http://localhost:8001/docs |
| product-service API | http://localhost:8002/docs |
| optimization-service API | http://localhost:8003/docs |
| MongoDB | localhost:27017 |

---

## Usuarios de prueba (seed)

| Usuario | Contraseña | Rol |
|---|---|---|
| `manufacturer01` | `Manufacturer01!` | Fabricante (Ana García) |
| `manufacturer02` | `Manufacturer02!` | Fabricante (Miguel Torres) |
| `reviewer01` | `Reviewer01!` | Gestor/Revisor (Carlos López) |

---

## Arquitectura

```
packaging-optimizer/
├── users-service/         FastAPI + MongoDB — auth JWT, RBAC, gestión usuarios
├── product-service/       FastAPI + MongoDB — familias, subfamilias, campañas, productos
├── optimization-service/  FastAPI + MongoDB — contenedores, reglas, motor optimización 3D, propuestas, render Plotly, PDF
├── frontend/              React 18 + Vite + TypeScript — UI fabricante y panel gestor
└── docker-compose.yml     Orquestación de todos los servicios
```

**Puertos:**
| Servicio | Puerto |
|---|---|
| frontend | 5173 |
| users-service | 8001 |
| product-service | 8002 |
| optimization-service | 8003 |
| MongoDB | 27017 |

---

## Variables de entorno

Las variables de entorno están configuradas directamente en `docker-compose.yml` con valores por defecto para desarrollo local. No es necesario crear ningún archivo `.env` para arrancar.

Las variables principales son:

| Variable | Servicio | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | users-service, optimization-service | `dev-secret-key` |
| `MONGO_URL` | todos los servicios | `mongodb://admin:admin123@mongo:27017` |
| `PRODUCT_SERVICE_URL` | optimization-service | `http://product-service:8002` |
| `USERS_SERVICE_URL` | optimization-service | `http://users-service:8001` |

> ⚠️ Para producción, cambiar `SECRET_KEY` por un valor seguro generado con `openssl rand -hex 32`.

---

## Funcionalidades principales

### Rol Fabricante
- Ver catálogo de productos propios con estado (pendiente / optimizado)
- Seleccionar un producto y talla para optimizar su embalaje
- Introducir dimensiones del artículo y tamaño de lote
- Obtener propuesta de embalaje con visualización 3D interactiva (Plotly)
- Descargar informe PDF generado automáticamente
- Aceptar o rechazar la propuesta

### Rol Gestor / Revisor
- Ver todos los productos del sistema y sus propuestas (aceptadas/rechazadas)
- Gestionar el catálogo de contenedores (crear, editar, eliminar con preview 3D)
- Configurar reglas de embalaje (orientación, apilado máximo) y asignarlas a familias/subfamilias de producto
- Consultar propuestas con filtros por estado y fabricante

### Rol Administrador
- Gestión de usuarios y roles

---

## Datos de prueba incluidos (seed)

Al arrancar desde cero se cargan automáticamente:

- **10 familias** de producto (Electrónica, Textil, Vidrio, Cerámica...)
- **30 subfamilias**
- **4 campañas** (Summer/Winter 2025 y 2026)
- **21 productos** con tallas, asignados a fabricante01 y fabricante02
- **3 contenedores** (Caja-S, Caja-M, Caja-L) con prioridades 1-3
- **3 reglas** (Máximo 2 capas de apilado, Siempre vertical, Siempre horizontal)
- **2 asignaciones** de reglas (subfamilias Vasos y Botellas → Siempre vertical)

---

## Parar los servicios

```bash
docker compose down
```

Para parar **y eliminar los datos** (reset completo):

```bash
docker compose down -v
```

---

## CI/CD

El repositorio incluye un workflow de GitHub Actions (`.github/workflows/ci.yml`) que se ejecuta en cada push y PR a `main`:
- Instala dependencias Python de cada servicio
- Ejecuta los tests con `pytest`
- Construye todas las imágenes Docker con `docker compose build`
