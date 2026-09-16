# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).

## Relanzar la app

Backend (API + base de datos) corre en Docker; el frontend corre aparte con Vite.

```bash
docker compose up -d       # backend (API en :8010, PostGIS en :5434)
npm run dev                 # frontend (:5173)
```

Si ya está levantado y solo cambiaste código del backend (el contenedor corre con `--reload`
y monta `./backend` como volumen, así que normalmente no hace falta reiniciar nada):

```bash
docker compose restart api
```

## Repositorio

Código alojado en GitHub: https://github.com/eladiocs/deforastation-compliance (privado).

## Migraciones (Alembic)

```bash
docker compose exec api alembic upgrade head          # aplicar migraciones pendientes
docker compose exec api alembic revision -m "mensaje"  # crear una nueva migración
```

## Despliegue en producción (Render + Supabase)

Mismo enfoque que en Droughtwatch (proyecto hermano): demo público, Render para
backend+frontend y Supabase para Postgres/PostGIS. Se probó Vercel para el frontend pero se
descartó — su importación detecta el repo como monorepo multi-servicio (backend FastAPI +
frontend Vite) y pide un `vercel.json` de "Services" para desplegar ambos; como el backend ya
vive en Render, se quedó todo en Render por simplicidad.

### 1. Base de datos — Supabase Postgres

1. Crea un proyecto **nuevo y dedicado** a deforcompliance (no reutilices uno de otra
   app/cliente: mezclar tablas de dos apps en la misma base de datos es más frágil — una
   migración o reset de una podría afectar sin querer a la otra).
   - Organización: la tuya. Nombre: `deforcompliance`.
   - Región: despliega el selector y elige una ciudad concreta cercana a España (p.ej.
     Frankfurt o Ireland) — no dejes el genérico "Europe".
   - Contraseña: usa "Generate a password" y guárdala ya en un gestor de contraseñas (la
     necesitas en el paso 3, pero no hace falta compartirla con nadie más).
   - **Desmarca "Enable Data API"**: esa opción expone una API REST pública (PostgREST)
     sobre tus tablas para usar con `supabase-js`. Este backend habla directo a Postgres vía
     SQLAlchemy/psycopg, no usa esa API — dejarla activa solo añadiría una segunda API sin
     control sobre las mismas tablas. Al desmarcarla, "Automatically expose new tables" deja
     de aplicar.
2. Habilita PostGIS: **Database > Extensions** → busca `postgis` → **Enable** (o desde el
   **SQL Editor**: `create extension if not exists postgis;`).
3. **Project Settings > Database > Connection string** → pestaña **Connection pooling** →
   copia el modo **Session** (puerto `5432`, host tipo
   `aws-0-<region>.pooler.supabase.com`) — es el adecuado para un backend persistente como
   el Web Service de Render (el modo *Transaction*, puerto 6543, es para entornos
   serverless/edge). El *host* directo (`db.<project>.supabase.co`) solo es alcanzable por
   IPv6 en el plan free, así que usa el pooler para evitar problemas de conectividad desde
   Render.
4. Para `DATABASE_URL` del backend, cambia el prefijo de ese URI de `postgresql://` a
   `postgresql+psycopg://` (driver que usa SQLAlchemy aquí), manteniendo usuario/contraseña/
   host/puerto/db tal cual te los da Supabase.

### 2. Backend — Render Web Service (Docker)

Dashboard → **New > Web Service** → conecta el repo `eladiocs/deforastation-compliance`. En
el formulario de creación:

- **Name**: `deforcompliance-api` (forma parte de la URL:
  `https://deforcompliance-api.onrender.com`).
- **Project**: opcional, se puede dejar sin asignar.
- **Language**: Render lo detecta como `Node` por defecto (ve el `package.json` de la raíz
  del repo) — **cámbialo a `Docker`** manualmente, si no busca un Dockerfile donde no hay uno.
- **Branch**: `main`.
- **Region**: `Frankfurt (EU Central)` — la más cercana a España.
- **Root Directory**: `backend` (vacío por defecto — sin esto Render busca el Dockerfile en
  la raíz del repo en vez de en `backend/Dockerfile`). Al ponerlo, el "Build Command" de Node
  desaparece y Render pasa a usar el `Dockerfile Path` (déjalo con su valor por defecto).
- **Instance Type**: `Free` sirve para el demo — aviso: se "duerme" tras 15 min sin tráfico
  y el primer request tras eso tarda ~30-50s en despertar. Si prefieres que responda siempre
  al instante, usa `Starter` (~7$/mes).
- **Advanced** (desplegar esa sección):
  - **Health Check Path**: `/health`
  - **Port**: `8000` (coincide con el puerto fijado en `backend/Dockerfile`, que es distinto
    del `8010` que se mapea en local vía `docker-compose.yml`)
  - **Auto-Deploy**: `On Commit` (por defecto) — cada push a `main` redespliega solo
  - **Environment Variables**:
    ```
    DATABASE_URL=postgresql+psycopg://...        # del paso 1, con el prefijo cambiado
    PYTHONPATH=/app
    GEE_SERVICE_ACCOUNT_EMAIL=...
    GEE_KEY_PATH=/etc/secrets/gee-key.json
    GEE_PROJECT_ID=...
    REPORTS_DIR=/app/reports
    REPORT_SIGNING_KEY_PATH=/etc/secrets/report-signing-key.pem
    CORS_ORIGINS=...                              # se rellena en el paso 3, tras desplegar el frontend
    ```
    Si te equivocas en alguna, se corrige después sin recrear el servicio: pestaña
    **Environment** → editar el valor → **Save Changes** dispara un redeploy automático con
    el valor corregido (o **Cancel Deploy** desde **Events** si quieres frenar el que está en
    curso primero).
  - **Secret Files**: añade dos —
    - **Filename** `gee-key.json` (solo el nombre, sin ruta — Render ya lo expone en
      `/etc/secrets/gee-key.json` automáticamente; si pones la ruta completa como filename
      acaba anidada, tipo `/etc/secrets/etc/secrets/gee-key.json`) y **Contents** = el
      contenido de tu `backend/secrets/gee-key.json` local.
    - **Filename** `report-signing-key.pem` y **Contents** = el contenido de tu
      `backend/secrets/report-signing-key.pem` local.
    Nunca subas esos archivos al repo (ya están en `.gitignore`).

Tras el primer deploy, aplica las migraciones. En el plan **Starter** o superior, desde la
pestaña **Shell** del servicio en Render:

```bash
alembic upgrade head
```

El plan **Free** no da acceso a esa pestaña. Alternativa: correrlo desde tu propio PC
apuntando al `DATABASE_URL` de Supabase (mismo comando y contraseña que pusiste en Render,
pero tecleado en tu propia terminal, nunca compartido en un chat/IA):

```bash
docker compose run --rm --no-deps -e DATABASE_URL="postgresql+psycopg://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres" api alembic upgrade head
```

### 3. Frontend — Render Static Site

1. Dashboard → **New > Static Site** → mismo repo `eladiocs/deforastation-compliance`.
2. **Name**: `deforcompliance-front` — ponlo bien desde la creación: renombrarlo después
   desde **Settings** puede dejar el botón "Save changes" sin activarse (bug visto en la
   práctica); más simple borrar y recrear el servicio que pelear con el rename.
3. **Branch**: `main`.
4. **Root Directory**: déjalo vacío/`.` (raíz — el `package.json` del frontend está ahí, no
   en `backend/`).
5. **Build Command**: `npm install; npm run build` (equivalente a `npm ci && npm run build`)
   — **Publish Directory**: `dist`.
6. **Environment Variable** (se hornea en el build, Vite la lee en build-time):
   `VITE_API_URL=https://deforcompliance-api.onrender.com`
7. Crear el Static Site y esperar al build.
8. Una vez tengas la URL pública del Static Site (tipo
   `https://deforcompliance-front.onrender.com`), vuelve al backend (paso 2) y pon
   `CORS_ORIGINS=https://deforcompliance-front.onrender.com` (o tu dominio propio si
   configuras uno) y redepliega el backend.

### 4. Verificación

- `GET https://<backend>.onrender.com/health` → `{"status": "ok"}`
- Abrir el Static Site en el navegador y comprobar que carga las parcelas (sin errores de CORS
  en la consola).
