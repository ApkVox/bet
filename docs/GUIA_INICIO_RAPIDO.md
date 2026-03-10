# 🚀 Guía de Inicio Rápido (Paso a Paso)

¡Hola! Si llegaste hasta aquí es porque quieres correr el proyecto "La Fija" en tu computadora o publicarlo en internet, pero quizás todos esos archivos y códigos te parecen intimidantes.

**¡No te preocupes!** Esta guía está diseñada para llevarte de la mano.

---

## 🛑 Paso 0: ¿Qué necesitas tener instalado?

Antes de empezar a cocinar, necesitamos los utensilios. Necesitarás tres cosas instaladas en tu computadora:

1. **Python (Versión 3.10 o superior):** Es el lenguaje en el que está escrito el cerebro del proyecto.
   - *¿Cómo instalo esto?* Entra a [python.org](https://www.python.org/downloads/), descarga la última versión e instálala. **¡Muy importante!** Durante la instalación en Windows, marca la casilla que dice *"Add Python a PATH"*.
2. **Git:** Es una herramienta para descargar código de internet.
   - *¿Cómo instalo esto?* Descárgalo desde [git-scm.com](https://git-scm.com/downloads) e instálalo dando "Siguiente" a todo.
3. **Un Editor de Texto (Recomendado):** Necesitas algo para ver el código. Te recomendamos **Visual Studio Code (VS Code)**.
   - Descárgalo en [code.visualstudio.com](https://code.visualstudio.com/).

---

## ⬇️ Paso 1: Descargar el proyecto (Clonar el repositorio)

"Clonar" significa hacer una copia exacta de este proyecto de internet a tu computadora.

1. Abre tu **Terminal** o **Símbolo del Sistema**. En Windows, presiona la tecla de `Windows`, escribe `cmd` y dale Enter.
2. Escribe el siguiente comando y presiona Enter:
   ```cmd
   git clone https://github.com/ApkVox/bet.git
   ```
3. Ahora, entra a la carpeta que acabas de descargar con este comando:
   ```cmd
   cd bet
   ```

---

## 🛠️ Paso 2: Preparar la "cocina" (El Entorno Virtual)

En Python, es buena práctica crear un "entorno virtual". Piensa en esto como una caja aislada para este proyecto, para que las herramientas que instalemos aquí no rompan otras cosas en tu computadora.

1. **Crea el entorno:** Escribe esto en tu terminal y dale Enter:
   ```cmd
   python -m venv mi_entorno
   ```
2. **Activa el entorno (¡Abre la caja!):**
   - Si estás en **Windows**, escribe:
     ```cmd
     mi_entorno\Scripts\activate
     ```
   - Si estás en **Mac o Linux**, escribe:
     ```cmd
     source mi_entorno/bin/activate
     ```
   *(Sabrás que funcionó si al inicio de la línea de tu terminal aparece `(mi_entorno)`)*

3. **Instala las dependencias (Las piezas del motor):** El archivo `requirements.txt` tiene la lista de compras de todo lo que la Inteligencia Artificial necesita para funcionar. Escribe:
   ```cmd
   pip install -r requirements.txt
   ```
   *Esto puede tardar un poco. Verás mucho texto moverse en la pantalla. ¡Es normal!*

---

## 🔑 Paso 3: Las Llaves Secretas (Variables de Entorno)

Nuestra aplicación necesita algunas contraseñas o "llaves" para hablar con otros servicios en internet. Como son secretas, no vienen en el código que descargaste.

1. Abre la carpeta del proyecto (`bet`) con tu Visual Studio Code.
2. Busca un archivo llamado `.env.example` (Es un archivo de ejemplo).
3. Haz una **copia** de ese archivo y renombra la copia para que se llame solamente **`.env`** (Punto env).
4. Dentro de ese archivo `.env`, verás algo como esto:
   ```env
   DEEPSEEK_API_KEY=pon_tu_llave_aqui
   ```
   Para conseguir esa llave gratuita de IA, lee nuestra guía de [Servicios y APIs Externas](SERVICIOS_Y_APIS.md). ¡Pero tranquilo! Puedes usar la aplicación en tu computadora la primera vez sin esa llave para ir probando.

---

## ▶️ Paso 4: ¡Encender los motores!

Ya casi terminamos. Ahora vamos a encender la aplicación web localmente (solo en tu computadora).

1. Asegúrate de que tu terminal tiene el entorno activado `(mi_entorno)`.
2. Escribe este comando mágico:
   ```cmd
   python production_server.py
   ```
3. Si todo salió bien, verás un texto diciendo que el servidor Uvicorn ha iniciado.

**¡La Fija ya está funcionando!**
- Abre tu navegador web favorito (Chrome, Edge, etc).
- En la barra de direcciones escribe: **`http://localhost:8080`**
- Deberías ver la página principal con las predicciones.

---

## ⚙️ Paso 5: El Panel de Control (Panel de Administrador)

El proyecto tiene una zona secreta para ver configuraciones y herramientas internas.

1. En tu navegador, ve a: **`http://localhost:8080/admin`**
2. **¡Alto ahí!** Te pedirá una contraseña. Como es la primera vez que entras, el sistema te mostrará una pantalla que dice: *"Primera vez: crea tu contraseña de administrador"*.
3. Inventa una buena contraseña, escríbela y guárdala en un lugar seguro. ¡Esa será tu llave para entrar la próxima vez!

*(Nota: En ocasiones excepcionales, si no te deja entrar, puedes forzar el reseteo abriendo otra terminal en la carpeta del proyecto, activando el entorno y escribiendo: `python admin_config.py set-password`, o añadiendo `RESET_ADMIN_PASSWORD=TuNuevaContraseña` en el archivo `.env` temporalmente).*

---

## 🎉 ¡Felicidades!

Ya has instalado y corrido un proyecto complejo de Inteligencia Artificial en tu propia máquina.

Si alguna vez quieres apagar el servidor, simplemente ve a la terminal donde lo iniciaste y presiona `Ctrl + C`.

Si quieres entender para qué sirven otros servicios externos complicados (como Render, Supabase o Resend), lee nuestra guía de [Servicios y APIs Externas](SERVICIOS_Y_APIS.md).
