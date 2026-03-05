### Contexto admin IA

Este documento describe en detalle cómo funciona actualmente el apartado de administración de la aplicación **La Fija**, con especial foco en el flujo de edición de promos (imágenes promocionales). Está pensado como referencia histórica antes de rehacer el panel de administración desde cero.

---

## 1. Visión general del apartado de administración

- **Objetivo principal**: permitir a un único administrador:
  - Gestionar el **tema y colores** del sitio.
  - Configurar el **branding** (nombre, subtítulo, emoji).
  - Activar/desactivar **features** (fútbol, descarga de promo, modo oscuro por defecto, análisis de IA).
  - Configurar un **banner de anuncio**.
  - Configurar claves de **publicidad (Adsterra)**.
  - Gestionar la **seguridad** del panel (contraseña y recuperación por email).
  - Ajustar visualmente el layout del **editor de promos** (posición de logos, textos, caja de predicción, etc.).

- **Tecnologías clave**:
  - Backend: `FastAPI` + `uvicorn` en `main.py`.
  - Módulo de configuración y seguridad: `admin_config.py`.
  - Generador de promos: `promo_generator.py`.
  - Frontend admin principal: `static/admin.html` + `static/js/admin.js`.
  - Editor de promo standalone: `static/promo_editor.html`.

- **Seguridad**:
  - Autenticación con **contraseña** (hash bcrypt).
  - Emisión de **tokens JWT** con rol `admin`.
  - Protecciones adicionales:
    - **Rate limiting** en intentos de login (5 intentos / 15 min por IP).
    - **Recuperación de contraseña** vía token enviado por email (Resend o SMTP).

---

## 2. Backend de administración en `main.py`

El archivo `main.py` define la API principal de la aplicación y contiene varios endpoints relacionados con el panel de administración.

### 2.1. Endpoints públicos relacionados con configuración

- **`GET /api/settings`**
  - Uso: devolver la configuración pública para el frontend principal.
  - Implementación:
    - Importa `get_public_config` desde `admin_config`.
    - Devuelve un diccionario con:
      - `theme`
      - `branding`
      - `features`
      - `announcement`
      - `ads`
    - En caso de error, devuelve valores por defecto vacíos y `ads.enabled = False`.
  - Es el puente entre los ajustes que el admin configura en el panel y el frontend público de usuarios.

### 2.2. Middleware y montado de estáticos

- El backend monta los estáticos con:
  - `app.mount("/static", StaticFiles(directory="static"), name="static")`
- El panel de administración se sirve en:
  - **`GET /admin`** → devuelve el archivo `static/admin.html`.

### 2.3. Utilidades de autenticación de admin

En `main.py` se definen helpers que dependen de `admin_config`:

- **`_admin_token(request: Request) -> Optional[str]`**
  - Extrae el token JWT del header `Authorization: Bearer <token>`.

- **`require_admin(request: Request)`**
  - Obtiene el token usando `_admin_token`.
  - Llama a `verify_token(token)` de `admin_config`.
  - Si no hay token o es inválido/expirado, lanza `HTTPException` 401.
  - Se usa como dependencia en endpoints protegidos (`Depends(require_admin)`).

### 2.4. Endpoints de autenticación y gestión de contraseña

Todos estos endpoints se apoyan en `admin_config.py`.

- **`POST /api/admin/login`**
  - Body esperado: `{ "password": "<contraseña>" }`.
  - Flujo:
    1. Valida presencia de `password`.
    2. Obtiene la IP del cliente (`request.client.host`) y la pasa a `check_rate_limit(ip)`.
    3. Carga configuración (`load_config()`), obtiene `password_hash`.
    4. Verifica la contraseña con `verify_password`.
       - Si falla, registra intento con `record_attempt(ip)` y devuelve 401.
    5. Si es correcta, genera un token con `create_token()` y lo devuelve como `{ "token": "<jwt>" }`.
  - Seguridad:
    - Rate limit a nivel de IP.
    - Hash de contraseña con bcrypt.
    - Tokens con expiración.

- **`GET /api/admin/needs-initial-password`**
  - Devuelve `{"needs_initial_password": true/false}`.
  - Lógica:
    - Lee el `password_hash` del archivo de configuración.
    - Si no hay hash (cadena vacía), se asume que es la primera vez y hay que crear la contraseña inicial.
  - Usado por el frontend para mostrar el flujo de “Crear contraseña inicial”.

- **`POST /api/admin/set-initial-password`**
  - Body: `{ "password": "<nueva_contraseña>" }`.
  - Flujo:
    1. Valida longitud mínima de 6 caracteres.
    2. Carga config; si ya existe `password_hash`, devuelve error (no permite sobreescribir una contraseña ya configurada).
    3. Genera `password_hash` con `hash_password` y lo guarda con `save_config`.

- **`POST /api/admin/password`**
  - Cambia la contraseña validando la actual, requiere sesión válida:
    - Valida token JWT con `verify_token` (no usa `Depends(require_admin)`, sino `_admin_token` + `verify_token` directamente).
  - Body:
    - `current_password`
    - `new_password`
  - Validaciones:
    - Longitud mínima para `new_password`.
    - Que exista `password_hash` configurado.
    - Que `current_password` sea correcta.
    - Que `new_password` no sea igual a la actual.
  - Actualiza `password_hash` y guarda configuración.

### 2.5. Endpoints de recuperación de contraseña por email

- **`GET /api/admin/email-recovery-status`**
  - Devuelve si el sistema de correo está configurado:
    - `resend_configured`: hay `RESEND_API_KEY`.
    - `recovery_email_configured`: hay `ADMIN_RECOVERY_EMAIL`.
    - `hint`: texto de ayuda si falta configuración.

- **`POST /api/admin/forgot-password`**
  - Body: `{ "email": "<correo_admin>" }`.
  - Flujo:
    1. Valida que se envíe `email`.
    2. Comprueba que haya `ADMIN_RECOVERY_EMAIL` configurado (env var).
    3. Llama a `create_password_reset_token(email)`:
       - Valida que el email coincida con el configurado.
       - Crea un token firmado y persistido en `password_reset_tokens.json` (o equivalente en `/tmp`).
    4. Construye `base_url` usando:
       - `RENDER_EXTERNAL_URL` o `SITE_URL` o `request.base_url`.
    5. Llama a `send_reset_email(email, token, base_url)`:
       - Preferencia por **Resend** (`RESEND_API_KEY`).
       - Si no hay Resend, intenta **SMTP** con `SMTP_HOST`, `SMTP_USER`, etc.
  - Respuesta amigable sin revelar si el email existe: siempre dice que se enviará un enlace “si el correo es el del administrador”.

- **`POST /api/admin/reset-password`**
  - Body:
    - `token`: token de reset recibido por email.
    - `new_password`: nueva contraseña.
  - Flujo:
    1. Valida presencia de token y longitud de `new_password`.
    2. Llama a `get_and_consume_reset_token(token)`:
       - Valida que el token exista y no esté expirado.
       - Lo borra al usarlo.
    3. Actualiza `password_hash` en config con la nueva contraseña y guarda.

### 2.6. Endpoints de configuración de administración

Estos endpoints permiten leer y guardar la configuración completa usada por el sitio.

- **`GET /api/admin/settings`** (protegido por `require_admin`)
  - Carga la configuración desde `admin_config.load_config()`.
  - Filtra para no enviar:
    - `password_hash`
    - `jwt_secret`
  - Devuelve:
    - `theme`
    - `branding`
    - `features`
    - `announcement`
    - `ads`

- **`POST /api/admin/settings`** (protegido por `require_admin`)
  - Body: diccionario con cualquier subconjunto de:
    - `theme`
    - `branding`
    - `features`
    - `announcement`
    - `ads`
  - Mezcla el body con la config existente y guarda el resultado con `save_config`.

---

## 3. Módulo `admin_config.py`

`admin_config.py` centraliza la configuración del panel de administración, seguridad y recuperación de contraseña.

### 3.1. Almacenamiento de configuración

- **Archivos y rutas**:
  - `admin_settings.json`: archivo principal con la configuración persistente.
  - `admin_settings.default.json`: archivo opcional con valores por defecto que se fusionan con `DEFAULT_SETTINGS`.
  - `password_reset_tokens.json`: archivo donde se guardan los tokens de recuperación de contraseña.
  - En casos sin permisos de escritura, se usan rutas alternativas en `/tmp` (por ejemplo, en Render free).

- **`DEFAULT_SETTINGS`**:
  - Estructura por defecto que define:
    - `password_hash`: hash de contraseña (vacío inicialmente).
    - `jwt_secret`: secreto para firmar JWT (se genera en `_get_jwt_secret()` si falta).
    - `theme`:
      - `light`: colores para modo claro (accent, bg, textos, success/danger/warning).
      - `dark`: colores para modo oscuro.
    - `branding`:
      - `title`: nombre del sitio (“La Fija”).
      - `subtitle`: descripción corta.
      - `emoji`: icono.
    - `features`:
      - `football`: activar sección de fútbol.
      - `promo_download`: mostrar botón para descargar promo.
      - `dark_default`: empezar en modo oscuro.
      - `ai_analysis`: mostrar análisis de IA.
    - `announcement`:
      - `enabled`: si hay banner activo.
      - `text`: mensaje del banner.
      - `color`: color del banner.
    - `ads`:
      - `enabled`: activar publicidad.
      - `left_key` y `right_key`: claves de banners Adsterra.

- **Funciones clave**:
  - `load_config()`:
    - Determina el archivo de settings con `_get_settings_file()`.
    - Si el archivo no existe:
      - Parte de `DEFAULT_SETTINGS`.
      - Si existe `admin_settings.default.json`, lo fusiona con `_deep_merge`.
      - Asegura `password_hash` vacío (para flujo de “primera contraseña”).
      - Guarda esa configuración inicial.
    - Si existe el archivo:
      - Lo lee y lo fusiona con `DEFAULT_SETTINGS`.
      - Soporta variables de entorno especiales:
        - `FORCE_INITIAL_PASSWORD`: fuerza a vaciar `password_hash` aunque ya hubiera contraseña.
        - `RESET_ADMIN_PASSWORD`: permite resetear la contraseña vía env (generando nuevo hash).
  - `save_config(config)`:
    - Guarda el JSON en el path determinado.
  - `get_public_config()`:
    - Devuelve sólo partes públicas (`theme`, `branding`, `features`, `announcement`, `ads`).

### 3.2. Seguridad: contraseñas y JWT

- **Password hashing**:
  - `hash_password(password)`:
    - Genera salt con `bcrypt.gensalt(rounds=12)`.
    - Devuelve hash como texto UTF-8.
  - `verify_password(password, hashed)`:
    - Usa `bcrypt.checkpw`.
    - Maneja errores devolviendo `False`.

- **JWT**:
  - `TOKEN_EXPIRY_HOURS = 1` → el token dura 1 hora.
  - `_get_jwt_secret()`:
    - Lee config.
    - Si no hay `jwt_secret`, genera uno con `secrets.token_hex(32)` y lo guarda.
  - `create_token()`:
    - Construye payload:
      - `role: "admin"`
      - `iat`: timestamp actual.
      - `exp`: `iat + TOKEN_EXPIRY_HOURS`.
    - Firma con algoritmo `HS256`.
  - `verify_token(token)`:
    - Decodifica con `jwt.decode`.
    - Maneja `ExpiredSignatureError` e `InvalidTokenError`, devolviendo `False` en esos casos.

### 3.3. Rate limiting de login

- Variables:
  - `_login_attempts`: diccionario `ip -> [timestamps]`.
  - `MAX_ATTEMPTS = 5`.
  - `WINDOW_SECONDS = 900` (15 minutos).

- Funciones:
  - `check_rate_limit(ip)`:
    - Limpia intentos antiguos fuera de la ventana.
    - Devuelve `False` si ya hay 5 o más intentos dentro de la ventana.
  - `record_attempt(ip)`:
    - Registra un nuevo intento fallido en la lista de timestamps de esa IP.

### 3.4. Recuperación de contraseña por token y correo

- **Archivos de tokens**:
  - `password_reset_tokens.json` o equivalente en `/tmp`.
  - Estructura: `token -> { "email": ..., "expires": ... }`.

- Funciones principales:
  - `create_password_reset_token(email)`:
    - Normaliza email a minúsculas.
    - Valida que `email` no esté vacío.
    - Compara contra `ADMIN_RECOVERY_EMAIL` (env).
    - Genera un token seguro con `secrets.token_urlsafe(32)`.
    - Asigna expiración `RESET_TOKEN_EXPIRE_MINUTES` (60 minutos).
    - Limpia tokens expirados.
    - Guarda el diccionario.
  - `get_and_consume_reset_token(token)`:
    - Valida que exista y no haya expirado.
    - Borra el token tras usarlo.
    - Devuelve el email asociado.

- **Envío de email**:
  - `send_reset_email(to_email, token, base_url)`:
    - Construye `reset_url = base_url + "/admin?reset=<token>"`.
    - Intenta primero **Resend**:
      - Usa `RESEND_API_KEY` y `RESEND_FROM`.
      - Hace POST a la API de Resend con HTML y texto plano.
    - Si no hay Resend:
      - Intenta **SMTP** con:
        - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM`.
    - Si no hay configuración válida:
      - Lanza `ValueError` con instrucciones para configurar envío.

### 3.5. CLI para establecer contraseña

- `cli_set_password()`:
  - Flujo interactivo en terminal:
    1. Pide nueva contraseña (oculta) y confirmación.
    2. Valida longitud y coincidencia.
    3. Genera `password_hash` y `jwt_secret` si falta.
    4. Guarda configuración.
  - Se ejecuta con:
    - `python admin_config.py set-password`

---

## 4. Frontend del panel de administración (`static/admin.html` + `static/js/admin.js`)

El panel de administración ofrece una experiencia rica para configurar el sitio. Consta de:

- Pantalla de **login / creación de contraseña / recuperación**.
- Un **dashboard** con sidebar y diferentes paneles (Theme, Branding, Features, Announcement, Ads, Promo, Security).

### 4.1. Pantalla de login

En `admin.html`:

- Elementos clave:
  - `#loginScreen`: contenedor de la vista de login.
  - `#loginCard`: tarjeta con:
    - Logo/emoji 🔐.
    - Formulario de login (`#loginForm`).
    - Bloque para crear contraseña inicial (`#setInitialPasswordBlock`).
    - Bloque para recuperación de contraseña (`#forgotPasswordBlock`).
  - Tarjeta separada `#resetPasswordCard` usada cuando se entra con `?reset=<token>` en la URL.

En `admin.js`:

- Gestión de token:
  - `TOKEN_KEY = "admin_token"` en `localStorage`.
  - `authToken` en memoria.
  - `setAuthToken(token)`: guarda o limpia el token.

- Flujo de login:
  - `handleLoginSubmit`:
    - Envía `POST /api/admin/login` con la contraseña.
    - Si OK:
      - Guarda token.
      - Llama a `loadSettings()` para traer config.
      - Llama a `showDashboard()` para entrar al panel.
    - Si error:
      - Muestra mensaje en `#loginError`.

- Primer uso (sin contraseña):
  - `refreshInitialPasswordState()`:
    - Llama a `GET /api/admin/needs-initial-password`.
    - Si `needs_initial_password` es `true`:
      - Muestra `#setInitialPasswordBlock` y oculta `#loginForm`.
  - `handleSetInitialPassword()`:
    - Valida las contraseñas.
    - Llama a `POST /api/admin/set-initial-password`.
    - Si OK, oculta bloque de password inicial y vuelve al login normal.

- Recuperación de contraseña:
  - `setupForgotPassword()`:
    - Maneja el enlace “¿Olvidaste tu contraseña?”:
      - Muestra `#forgotPasswordBlock`.
      - Llama a `GET /api/admin/email-recovery-status` para mostrar `hint` si falta configurar algo.
    - Enviar email:
      - Botón `#sendResetBtn` llama a `POST /api/admin/forgot-password`.
  - `handleResetByTokenIfPresent()`:
    - Si la URL tiene `?reset=<token>`, oculta tarjeta de login y muestra `#resetPasswordCard`.
    - El formulario `#resetPasswordForm` envía `POST /api/admin/reset-password` con token + nueva contraseña.

### 4.2. Navegación y estructura del dashboard

- Sidebar:
  - Botones `.nav-item` con `data-panel`:
    - `theme`
    - `branding`
    - `features`
    - `announcement`
    - `ads`
    - `promo`
    - `security`
  - Botón de logout (`.nav-item.logout`) que llama a `logout()`.

- `setupNavigation()`:
  - Asigna listeners a cada `.nav-item`.
  - Activa el panel correspondiente:
    - Muestra `#panel-<data-panel>`.
    - Cambia el título `#panelTitle` usando `PANEL_TITLES`.
  - En particular, al acceder al panel `promo` llama a `loadPromoConfig()` para cargar la configuración de promos.

### 4.3. Carga y guardado de configuración general

- `loadSettings()`:
  - Llama a `GET /api/admin/settings` (requiere token).
  - Guarda la respuesta en la variable global `settings`.
  - Llama a `populateAllFields()`.

- `populateAllFields()`:
  - **Theme**:
    - Usa `renderColorInputs` para poblar inputs de colores de modo oscuro (`#darkColorInputs`) y modo claro (`#lightColorInputs`).
  - **Branding**:
    - `#brandTitle`, `#brandEmoji`, `#brandSubtitle`.
  - **Features**:
    - `#featFootball`, `#featPromo`, `#featDark`, `#featAI`.
  - **Announcement**:
    - `#annEnabled`, `#annText`, `#annColorPicker`, `#annColorText`.
    - Llama a `updateAnnouncementPreview()` para actualizar el bloque de vista previa `#annPreview`.
  - **Ads**:
    - `#adsEnabled`, `#adsLeftKey`, `#adsRightKey`.

- `gatherSettings()`:
  - Recolecta todos los valores actuales del formulario en un objeto con la misma estructura que usa el backend.

- `saveSettings()`:
  - Envía `POST /api/admin/settings` con el resultado de `gatherSettings()`.
  - Si se guarda correctamente, muestra un toast de éxito.

- `resetThemeDefaults()`:
  - Restaura el objeto `settings.theme` a los valores hardcodeados de tema oscuro/claro por defecto.
  - Vuelve a llamar a `renderColorInputs` para recargar los inputs.

### 4.4. Panel de seguridad en el dashboard

- Cambiar contraseña:
  - Inputs `#secCurrent` (contraseña actual) y `#secNew` (nueva).
  - Botón que llama a `changePassword()`.
  - `changePassword()`:
    - Valida longitud mínima.
    - Envía `POST /api/admin/password` con `current_password` y `new_password`.
    - Muestra toasts de éxito o error.

- Información de sesión:
  - Panel estático que informa:
    - Que la sesión está activa.
    - Que la expiración es 1 hora.
    - Que la protección es bcrypt + JWT.
    - Que existe rate limit de 5 intentos / 15 min.

---

## 5. Editor de promos: flujo completo

El sistema de promos está compuesto por:

1. **Backend de generación de imagen** (`promo_generator.py`).
2. **Endpoint de preview** (`/api/promo-editor-preview`) en `main.py`.
3. **Endpoint de generación para descarga** (`/api/promo-image`).
4. **API de configuración de layout** (`/api/promo-config`).
5. **UI de edición dentro del panel de admin** (panel “Editor Promo” en `admin.html` + `admin.js`).
6. **UI standalone de edición** (`promo_editor.html`).

### 5.1. Generador de promos (`promo_generator.py`)

- Configuración:
  - `DEFAULTS`: diccionario con todos los parámetros visuales:
    - Posición y tamaño de logos:
      - `logo_cy`: eje Y del centro de los logos.
      - `logo_left_cx`: coordenada X del logo izquierdo.
      - `logo_right_offset`: distancia desde el borde derecho para el logo derecho.
      - `logo_max`: tamaño máximo del logo.
    - Nombres de equipo:
      - `names_y`: posición vertical.
      - `names_font_size`: tamaño de fuente.
      - `names_max_w`: ancho máximo para el texto (para cortar/multiplicar líneas).
      - `names_color`: color hex.
    - Caja de predicción:
      - `box_y0` / `box_y1`: top y bottom de la caja.
      - `box_pad_x`: padding horizontal.
      - `box_radius`: radio de las esquinas.
      - `box_border_w`: grosor del borde.
      - `box_border_color`: color del borde.
    - Etiqueta (“A GANAR EL PARTIDO”):
      - `label_offset_y`: desplazamiento desde el top de la caja.
      - `label_font_size`: tamaño de fuente.
      - `label_color`: color.
    - Nombre del ganador:
      - `winner_offset_y`, `winner_font_size`, `winner_color`.
    - Porcentaje:
      - `prob_offset_y`, `prob_font_size`, `prob_color`.
    - Footer:
      - `footer_y`, `footer_font_size`, `footer_color`.
    - Toggles de visibilidad:
      - `show_logos`, `show_names`, `show_box_border`, `show_label`, `show_winner`, `show_prob`, `show_footer`.

- Funciones principales:
  - `load_config()`:
    - Carga `promo_config.json` si existe.
    - Fusiona `DEFAULTS` con la configuración guardada (los valores guardados sobrescriben los defaults).
  - `save_config(cfg)`:
    - Persiste el diccionario de configuración en `promo_config.json`.
  - `generate_promo_image(home_team, away_team, winner, probability, status=None, config_override=None)`:
    - Carga el template base (`promo_v3_template.png`).
    - Mezcla configuración:
      - `DEFAULTS` → config guardada → `config_override` (sobrescribe).
    - Dibuja logos si `show_logos` es `True`:
      - Busca logos en `static/img/nba_logos`.
    - Dibuja nombres de equipos si `show_names` es `True`.
    - Dibuja la caja de predicción si `show_box_border` es `True`.
    - Dibuja la etiqueta “A GANAR EL PARTIDO” si `show_label` es `True`.
    - Dibuja nombre del ganador, porcentaje y footer según toggles.
    - Si `status` es `GANADA` o `PERDIDA`, dibuja un badge de estado arriba (“✅ ACERTADA” o “❌ FALLADA”).
    - Devuelve la imagen en bytes PNG.

### 5.2. Endpoints relacionados con promos en `main.py`

- **`GET /api/promo-editor-preview`**
  - Pensado para el **editor de promo** (tanto el integrado en admin como el standalone).
  - Parámetros de query:
    - `home_team`, `away_team`, `winner`, `probability`.
    - Todos los campos de layout (`logo_cy`, `names_y`, etc.).
    - Toggles (`show_logos`, `show_names`, etc.) como strings (`true/false`).
  - Implementación:
    - Usa `_parse_promo_query(request)` para:
      - Extraer equipos, ganador y probabilidad.
      - Construir `config_override` con:
        - Todos los valores int parseados.
        - Colores.
        - Banderas booleanas a partir de strings.
    - Llama a `generate_promo_image(..., config_override=config_override)`.
    - Devuelve `image/png` como respuesta.
  - Importante:
    - **No persiste** la configuración. Sólo genera un preview en tiempo real según los parámetros recibidos.

- **`GET /api/promo-image`**
  - Uso: generar la imagen final descargable para un partido concreto.
  - Parámetros:
    - `home_team`, `away_team`, `winner`, `probability`.
    - `status` (`PENDING`, `WIN`, `LOSS`, `GANADA`, `PERDIDA`) para mostrar badge si aplica.
  - Implementación:
    - Valida parámetros obligatorios.
    - Normaliza `status` a `GANADA` o `PERDIDA` (o `None`).
    - Llama a `generate_promo_image` **sin overrides**, usando config persistida.
    - Responde con PNG.

- **`GET /api/promo-config`** y **`POST /api/promo-config`**
  - Protegidos por `require_admin`.
  - `GET`:
    - Llama a `promo_generator.load_config()` y devuelve el diccionario completo.
  - `POST`:
    - Recibe un JSON con las claves de layout (y toggles).
    - Llama a `promo_generator.save_config(body)`.
  - Esta API es el vínculo entre el editor de promo (frontend) y el archivo `promo_config.json`.

### 5.3. Editor de promo dentro del panel de admin (`panel-promo`)

En `admin.html`, dentro de `#panel-promo`:

- Sección “Editor Visual de Promo” con:
  - Columna de preview:
    - Imagen `#promoPreviewImg` que se actualiza llamando a `/api/promo-editor-preview`.
    - Botón “🔄 Actualizar” que llama a `updatePromoPreview()`.
  - Columna de controles:
    - Campos de “EQUIPOS DE PRUEBA”:
      - `#promo_test_home`, `#promo_test_away`, `#promo_test_winner`, `#promo_test_prob`.
    - Secciones agrupadas:
      - LOGOS
      - NOMBRES
      - BORDE CAJA
      - ETIQUETA
      - GANADOR
      - PORCENTAJE
      - FOOTER
    - Cada sección tiene:
      - Sliders (`input[type="range"]`) con valores mínimos, máximos y por defecto.
      - Checks para toggles (por ej. `#p_show_logos`).
      - Selectores de color (`input[type="color"]`).

En `admin.js`:

- Constantes:
  - `PROMO_FIELDS`: lista de nombres de campos numéricos o de color.
  - `PROMO_TOGGLES`: lista de toggles booleanos.
  - `PROMO_DEFAULTS`: objeto con los valores por defecto de todos los campos y toggles.

- Funciones:
  - `pSlider(el)`:
    - Actualiza el texto de valor junto al slider.
    - Usa un `setTimeout` con `promoDebounce` para llamar a `updatePromoPreview()` después de un pequeño delay, evitando demasiadas peticiones.
  - `getPromoParams()`:
    - Lee:
      - Equipos y probabilidad de prueba.
      - Todos los `PROMO_FIELDS` desde elementos con IDs `p_<campo>`.
      - Todos los `PROMO_TOGGLES` desde los checkboxes `p_<toggle>`.
    - Construye un objeto con todos esos valores.
  - `updatePromoPreview()`:
    - Convierte `getPromoParams()` en query string `URLSearchParams`.
    - Actualiza `src` de `#promoPreviewImg` apuntando a `/api/promo-editor-preview?...&_t=<timestamp>`.
  - `savePromoConfig()`:
    - Toma `getPromoParams()`.
    - Construye un objeto `config` que sólo contiene `PROMO_FIELDS` y `PROMO_TOGGLES` (sin equipos de prueba).
    - Envía `POST /api/promo-config` con ese `config`.
  - `loadPromoConfig()`:
    - Llama a `GET /api/promo-config`.
    - Recorre `PROMO_FIELDS` y `PROMO_TOGGLES` para:
      - Rellenar sliders, colores y checks con los valores guardados.
      - Actualizar los textos de valor asociados (`*_v`).
    - Llama a `updatePromoPreview()` al final.
  - `resetPromoDefaults()`:
    - Restaura valores de `PROMO_DEFAULTS` en todos los sliders y colores.
    - Activa todos los toggles.
    - Llama a `updatePromoPreview()` y muestra un toast informativo.

### 5.4. Editor de promo standalone (`static/promo_editor.html`)

Este archivo implementa otro editor de promo más antiguo (o destinado a un uso distinto) pero con el mismo backend de `promo_generator`.

- Layout:
  - Panel izquierdo:
    - Imagen de preview `#preview-img`.
    - Botones:
      - “🔄 Actualizar” → `updatePreview()`.
      - “💾 Guardar Config” → `saveConfig()`.
      - “↩ Reset” → `resetDefaults()`.
  - Panel derecho:
    - Título “⚙️ Editor de Promo”.
    - Secciones análogas a las del panel en admin:
      - Equipos de prueba.
      - Posición de logos.
      - Nombres de equipo.
      - Caja de predicción.
      - Etiqueta.
      - Ganador.
      - Porcentaje.
      - Footer.

- JS inline:
  - `getParams()`:
    - Similar a `getPromoParams()` en `admin.js`, pero sin toggles `show_*`.
  - `updatePreview()`:
    - Llama a `/api/promo-editor-preview` pasando los parámetros como query string.
  - `getAdminAuthHeaders()`:
    - Toma el token `admin_token` de `localStorage` para enviar en la cabecera `Authorization`.
  - `saveConfig()`:
    - Igual que `savePromoConfig()`, pero:
      - Envía `POST /api/promo-config` con la configuración de layout (sin equipos).
  - `resetDefaults()`:
    - Restaura un conjunto de valores por defecto similar al de `PROMO_DEFAULTS`.
  - `loadConfig()`:
    - Llama a `GET /api/promo-config`.
    - Si responde OK:
      - Pone los valores de cada campo.
    - Luego llama a `updatePreview()`.

En resumen, tanto el panel “Editor Promo” en `admin.html` como `promo_editor.html` apuntan a los mismos endpoints `/api/promo-editor-preview` y `/api/promo-config`, y ambos configuran el mismo archivo `promo_config.json` que consume `promo_generator.py`.

---

## 6. Flujo completo típico de uso del admin

1. El administrador abre `/admin` y se encuentra con la pantalla de login.
2. Si es la primera vez:
   - El frontend detecta que `needs_initial_password` es `true`.
   - Muestra el formulario para crear la **contraseña inicial**.
3. En usos posteriores:
   - El admin introduce su contraseña.
   - El backend valida con bcrypt y rate limiting.
   - Si es correcto, emite un **JWT** y el frontend lo almacena en `localStorage`.
4. El frontend llama a `GET /api/admin/settings` para cargar configuración.
5. El admin interactúa con los distintos paneles:
   - **Theme**: ajusta colores, luego “Guardar cambios”.
   - **Branding**: cambia títulos/emoji.
   - **Features**: activa fútbol, descarga de promo, etc.
   - **Announcement**: define un banner (texto y color).
   - **Ads**: configura claves de banners.
   - **Security**: cambia su contraseña si lo desea.
   - **Promo**:
     1. Configura equipos de prueba para tener un contexto visual.
     2. Ajusta sliders y colores para logos, textos y caja.
     3. Observa la vista previa generada por `/api/promo-editor-preview`.
     4. Cuando queda satisfecho, pulsa “Guardar configuración”.
     5. La configuración se persiste en `promo_config.json` vía `/api/promo-config`.
6. El frontend público del sitio:
   - Llama a `GET /api/settings` para obtener `theme`, `branding`, etc.
   - Muestra el sitio conforme a dichos ajustes.
7. Cuando un usuario del sitio descarga una promo:
   - El frontend llama a `/api/promo-image` con los datos del partido.
   - El backend carga `promo_config.json`, genera la imagen con `promo_generator` y la devuelve.

---

## 7. Puntos clave a tener en cuenta para rehacer el panel desde cero

Aunque este documento es descriptivo, destaca algunos conceptos que conviene preservar o rediseñar conscientemente al construir el nuevo panel:

- **Modelado de configuración**:
  - Actualmente se almacena en JSON plano (`admin_settings.json` y `promo_config.json`).
  - Estructuras bien separadas: `theme`, `branding`, `features`, `announcement`, `ads`, y por otro lado el config de promo.

- **Seguridad**:
  - Contraseñas con bcrypt.
  - JWT con expiración y rol `admin`.
  - Rate limit básico pero efectivo (por IP).
  - Flujo completo de recuperación de contraseña con email y tokens temporales.

- **Editor de promo**:
  - Layout completamente configurable pero acotado a un conjunto de parámetros numéricos y de color.
  - Preview en tiempo real usando parámetros en query string (sin tocar config guardada).
  - Endpoint separado para persistir la configuración real (`/api/promo-config`).

Este contexto sirve como referencia total del diseño actual antes de eliminar la implementación y empezar un nuevo panel de administración desde cero.

