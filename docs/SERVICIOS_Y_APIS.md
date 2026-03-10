# 🧩 Entendiendo los Servicios y APIs Externas

Si ya leíste la [Guía de Inicio Rápido](GUIA_INICIO_RAPIDO.md), o estabas configurando el archivo `.env`, probablemente te cruzaste con nombres de servicios en internet.

A primera vista, todos estos nombres (Render, Supabase, API, DeepSeek) pueden sonar muy confusos y abrumadores. Aquí te explicaremos qué son, por qué los usamos, y para qué sirven, de la manera más clara posible.

---

## 🚀 1. El Proveedor de Casa: *Render*

### ¿Qué es?
Render es una empresa en internet que presta "computadoras" en la nube donde nosotros alojaremos nuestra aplicación web. Imagina que alquilamos un apartamento donde nuestro programa va a vivir 24/7.

### ¿Para qué lo usamos?
Si corres "La Fija" en tu computadora (con la Guía de Inicio Rápido), tú eres el dueño del apartamento. Pero si apagas la computadora, la aplicación se cae. Por eso la subimos a Render; ellos la mantienen prendida (¡y gratis!).

Para que Render se mantenga gratis y no "se duerma", usamos otra página web que hace la función de un timbre (un "ping"). Esta página es **cron-job.org**. Cada 5 minutos entra a tocar el apartamento para despertar a Render y que siga despierto.

---

## 🤖 2. El "Detective" de Noticias: *DeepSeek* y su "API Key"

### ¿Qué es?
DeepSeek es una de las inteligencias artificiales "generalistas" modernas (semejante a ChatGPT, pero de otra compañía).
Una **API Key** (o "llave") es un código secreto larguísimo de letras y números que te entregan para que tú le des órdenes. Es como tu carné de membresía con ellos.

### ¿Para qué lo usamos?
Nosotros no le decimos a DeepSeek "Oye, hazme la tarea de matemáticas".
El sistema de "La Fija" tiene código que, automáticamente por detrás, se conecta a DeepSeek y le ruega:
> *"Oye DeepSeek, busca en internet cómo amaneció LeBron James hoy y dime si jugará el partido, o si está lesionado resúmeme la noticia. Y de paso, haz una recomendación".*

### ¿Cómo saco esa llave para que todo funcione?
1. Ve a su [plataforma para desarrolladores](https://platform.deepseek.com/).
2. Regístrate (créate una cuenta como en cualquier web).
3. Entra a la opción llamada **"API Keys"**.
4. Dale al botón "Create new API key" (Crea una nueva llave).
5. Ponle un nombre para acordarte (ej. "Mi llave para La Fija").
6. Te arrojarán ese largo código secreto (empieza con "sk-…").
7. Cópialo y pégalo en tu archivo `.env` en la variable `DEEPSEEK_API_KEY=tu_codigo_aqui_sk...` ¡Y listo, tu detective está activo para buscar noticias y hacer recomendaciones!

*(Ojo: Si no le pones la llave, el sistema funciona de igual manera y puede predecir quién gana, pero no dará noticias ni "recomendaciones de apuestas" con IA).*

---

## 🗄️ 3. El Armario Seguro: *Supabase*

### ¿Qué es?
Supabase es una empresa que te regala un espacio para crear Bases de Datos ("armarios" digitales súper organizados).

### ¿Para qué lo usamos?
Dijimos que **Render** es un apartamento que nos prestan gratis. Lo malo del apartamento gratuito de Render, es que... *te tiran todo a la basura cada vez que haces un cambio*. Su disco duro (su memoria) se vacía con cada actualización que subas.
Si cambias un color del tema de "La Fija" hoy, Render no se acordara si lo apagas.

Por lo tanto, le pedimos a Supabase que sea nuestro Armario. Guardaremos las **contraseñas de los administradores**, el **tema de colores** de la web y otras cosillas como las de la **promoción** ahí dentro. Así, por más que el apartamento gratuito pierda su disco duro, La Fija se conectará corriendo al armario (Supabase) que está seguro y preguntará "Oye, ¿qué colores tenía configurados?".

### ¿Cómo abro un armario allí?
1. Regístrate en [supabase.com](https://supabase.com).
2. Toca "New Project". (Te pedirán nombre y contraseña para tu armario).
3. Una vez creado el armario grande ("Project"), busca en su interfaz la sección **SQL Editor**. (A la izquierda, suele ser un ícono cuadrado con `/` adentro).
4. Dentro del editor, tienes un espacio en blanco enorme. Tienes que copiar un texto especial y pegarlo ahí adentro. Ese texto especial está guardado en este proyecto, en un archivo llamado `/scripts/init_app_config.sql`. Lo pegas entero, y le das "Correr/Run". ¡Magia, te acaba de crear los organizadores dentro de tu armario!
5. Para conectarnos, ve a "Project Settings" (Configuraciones) -> "Database" (Base de Datos) -> Busca "Connect" -> Usa "Connection string" y una opción llamada **"Session mode"** (porque Render es viejito en conexiones y usa IPv4).
6. Te darán un link laaaaaaargo que se ve algo así: `postgresql://postgres.[tu_nombre_del_armario]:[tu_contraseña]@aws-0-[ubicacion].pooler.supabase.com:5432/postgres`. (Copia todo y no te olvides cambiar el pedacito de  `[YOUR-PASSWORD]` por la contraseña de armario que inventaste al crear el proyecto.
7. Al igual que DeepSeek, pones esa ruta bajo tu variable mágica llamada `DATABASE_URL` en tu archivo `.env` local, o en las variables "Environment" o Variables de entorno de Render para Producción.

*(Nota: En Supabase la "Database password" es la contraseña general del armario que llenaste recién le diste al botón en el Paso 2).*

---

## ✉️ 4. El Mensajero para Recuperar Claves: *Resend*

### ¿Qué es?
Imagina que de repente de tantas contraseñas diferentes, te olvidas la clave para entrar al panel de Administrador local (y tu armario estaba en Supabase y ya perdiste la clave de Supabase e hiciste un caos). Necesitas recuperación al correo, ¿verdad? Resend es justamente el "cartero".

### ¿Para qué lo usamos?
Render Gratis nos dice: "Yo no envío correos directos gratis por seguridad", es decir, cierran la caja de correos. Para mandar nuestro correo, necesitamos que Resend lo haga por nosotros, ya que su puerta sí la pueden abrir.

### ¿Cómo configurarlo?
1. Necesitas una cuenta en [resend.com](https://resend.com).
2. Crear un token API Key (muy al estilo DeepSeek) en [resend.com/api-keys](https://resend.com/api-keys) tocando "Create API Key". Cópiala, tiene que empezar en "re_…".
3. Luego, agrega la información de abajo tanto a tu archivo `.env` o tu "Environment" de Render:
  -  `ADMIN_RECOVERY_EMAIL`: A dónde te enviarás el mensaje como Administrador Principal. Ejemplo: `tucorreo@tuempresa.com`.
  -  `RESEND_API_KEY`: Pega aquí el Token que copiaste gigante. Empezando por "re_".
  -  `RESEND_FROM`: El nombre del Cartero. Como lo envías desde su sistema gratis, en realidad no tienes "Tu Nombre", pones algo como: `La Fija <onboarding@resend.dev>`.
  -  `RENDER_EXTERNAL_URL`: Es la URL completa pública en internet de tu aplicación, como: `https://la-fija.onrender.com` (Y si tienes un dominio personalizado `https://la-fija.net` pones eso, esto es para que pueda darte un hipervínculo que toques dentro del correo).

---

## ⚙️ 5. El Empleado Fantasma (GitHub Actions / CRON)

### ¿Qué es "CRON"?
Es un temporizador invisible de los programadores. Tú le puedes decir a la computadora "Todos los domingos a las 3:00 de la tarde haz la cama para mí". Eso mismo hace el empleado invisible, GitHub, por ti a la misma hora del servidor todos los días.

### ¿Para qué lo usamos?
La aplicación principal (la que pusimos en Render) vive de lo rápido que responde. Su cerebro no tiene la capacidad de durar 45 minutos bajando los datos de ESPN y calculando números sin que colapse.
Por ende, le decimos a GitHub Actions, en su poderoso servidor gigante:
1. "Empieza a trabajar tú a las 3:00 AM".
2. "Baja todos los datos pesados".
3. "Analízalos como loco".
4. "Túmbalos y cópialos como un papel pequeñito final en el cuarto chiquito de Render (o más específicamente, en nuestro repositorio de GitHub para que lo agarre), y vete a dormir de nuevo".

Así, la aplicación te muestra las predicciones "ya cocinadas", lo cual la hace muy muy rápida y requiere cero RAM (Memoria). ¡Todo funciona y fluye casi en milisegundos!
