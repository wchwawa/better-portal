## Créditos

El método original para ajustar el bitrate procede de **[@atameric](https://github.com/atameric)** y [ps5-portal-high-bitrate](https://github.com/atameric/ps5-portal-high-bitrate). Puedes [apoyar al creador original](https://buymeacoffee.com/atameric).

Bajo licencia [MIT](LICENSE). Software independiente de la comunidad; sin afiliación con Sony ni PlayStation.

# Better Portal

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **Español** · [Français](README.fr.md) · [Türkçe](README.tr.md)

Elige un objetivo de mayor calidad de imagen al jugar a tu PS5 desde PlayStation Portal. Better Portal te guía por la configuración en **macOS o Windows**, una pantalla a la vez.

[Inicio rápido en macOS](#macos-quick-start) · [Inicio rápido en Windows](#windows-quick-start) · [Primera sesión](#first-session) · [Buscar las direcciones](#find-device-addresses) · [Resolver problemas](#questions-and-fixes)

## Antes de empezar

Ten preparado lo siguiente:

- Un **Mac o PC con Windows 10/11**, una **PS5** y una **PlayStation Portal**. Portal ya debe permitirte jugar a tu propia PS5 mediante Uso a distancia.
- Los tres conectados a tu **router habitual de casa**. El ordenador y Portal pueden usar el Wi-Fi; PS5 puede usar el mismo Wi-Fi o un cable de red a ese router. Evita la red de invitados y desconecta la VPN del ordenador si la utilizas.
- Acceso a Internet para la instalación y permiso para autorizar Better Portal en el ordenador.

Es una herramienta comunitaria experimental. Empieza con **65 Mbps**. El bitrate indica cuántos datos de imagen se pueden enviar cada segundo; aumentarlo puede mejorar los detalles, pero también causar tirones si la conexión es inestable.

<a id="get-started"></a>

## Inicio rápido

Solo necesitas instalar una vez. Conserva toda la carpeta descargada: contiene el archivo que abrirás cada vez que quieras jugar.

Elige las instrucciones para **tu ordenador**. Setup instala las dependencias una vez; Start abre el asistente para cada nueva conexión de Portal.

| Tu ordenador | Primera instalación | Iniciar una sesión |
| --- | --- | --- |
| **macOS** | Doble clic en **Setup.command** | Doble clic en **Start.command** |
| **Windows 10 / 11** | Doble clic en **Setup-Windows.cmd** | Doble clic en **Start-Windows.cmd** |

<a id="macos-quick-start"></a>

### Inicio rápido en macOS

<a id="install-python"></a>

1. **Instala Python:** abre la [página oficial de Python para Mac](https://www.python.org/downloads/macos/), elige un **Python 3.14 macOS installer** y abre el `.pkg` descargado. Sigue **Continuar → Instalar**. Si ya tienes Python 3.10 o posterior, puedes conservarlo.
2. **Completa la instalación de Python:** en Finder, abre **Aplicaciones → Python 3.14** y haz doble clic en **Install Certificates.command**. Espera a `update complete` y cierra la ventana. Para otra versión, usa su carpeta de Python correspondiente. Consulta las [instrucciones oficiales](https://docs.python.org/3.14/using/mac.html).
3. **Descarga Better Portal:** [descarga el ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip), abre **Finder → Descargas** y haz doble clic en el ZIP para descomprimirlo. Abre la carpeta **better-portal-main**.
4. **Configura una vez:** haz doble clic en **Setup.command**. Se abrirá Terminal. Espera a **`Setup complete.`**, pulsa **Return** y cierra la ventana.
5. **Inicia una sesión:** haz doble clic en **Start.command** dentro de la misma carpeta. Si aparece **`Password:`**, introduce tu **contraseña de inicio de sesión del Mac** y pulsa **Return**. **No se muestran letras ni puntos al escribir; es normal.** Continúa con [Primera sesión](#first-session).

Si macOS bloquea un archivo, consulta [«macOS no abre el archivo»](#macos-blocked). Si la instalación falla, consulta [Preguntas y soluciones](#questions-and-fixes) antes de iniciar una sesión.

<a id="windows-quick-start"></a>

### Inicio rápido en Windows

1. **Instala Python:** abre la [página oficial de Python para Windows](https://www.python.org/downloads/windows/) e instala **Python 3.14 de 64 bits (x86-64)** con el **lanzador `py`**. También puedes usar una instalación compatible existente de Python x86-64 3.10–3.14.
2. **Instala Npcap:** descárgalo de [npcap.com](https://npcap.com/#download). Deja **sin marcar el modo de compatibilidad con WinPcap**; no necesitas modo monitor de Wi-Fi ni soporte raw 802.11. Estas opciones siguen las [instrucciones de Scapy para Windows](https://scapy.readthedocs.io/en/stable/installation.html#windows).
3. **Descarga Better Portal:** [descarga el ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip). En **Explorador de archivos → Descargas**, haz clic derecho en el ZIP → **Extraer todo** y abre la carpeta **better-portal-main** extraída.
4. **Configura una vez:** haz doble clic en **Setup-Windows.cmd**. Espera a **`Setup complete`** y pulsa una tecla para cerrar la ventana. Si fallan las comprobaciones sin conexión, resuelve el error antes de iniciar una sesión.
5. **Inicia una sesión:** haz doble clic en **Start-Windows.cmd** en la misma carpeta y acepta la **solicitud de permisos de Windows**. Continúa con [Primera sesión](#first-session).

Windows utiliza el mismo asistente, idiomas, ajustes y cuenta atrás de 120 segundos. En Dispositivos aparece un selector de **adaptador LAN del PC**. Las pruebas con dispositivos reales en Windows siguen en curso; consulta la [guía de Windows (en inglés)](WINDOWS.md) para ver los requisitos y resolver problemas.

**En ambas plataformas:** conserva toda la carpeta extraída y abre su archivo Start para cada nueva sesión. Se guardan las direcciones, el idioma y el bitrate. Puedes instalar y abrir la aplicación haciendo doble clic en estos archivos; no necesitas editar código.

<a id="first-session"></a>

## Tu primera sesión

**Maneja el asistente con el teclado de tu ordenador.** Haz clic una vez dentro de Terminal para que reciba las pulsaciones. Los botones de colores se seleccionan con las teclas. **Return** o **Retorno** en el Mac es la tecla que la pantalla llama **Enter**.

| Tecla | Función |
| --- | --- |
| **Return / Enter** | Confirmar una elección, pasar al siguiente campo o activar el botón seleccionado. |
| **Tab** o **↑ / ↓** | Moverte entre los campos de los dispositivos. `>` marca la fila actual. |
| **← / →** | Cambiar el bitrate cuando su fila está seleccionada. `[x]` indica la opción elegida. |
| **S** | Abrir los ajustes para cambiar el idioma. Pulsa la letra una vez; no hace falta Return. |

Las imágenes muestran **la aplicación real en modo demo en Mac**. Windows sigue los mismos pasos y utiliza un selector de adaptador del PC en lugar del campo de interfaz del Mac. La etiqueta `DEMO` y las direcciones son ejemplos. **Usa las direcciones de tus dispositivos y sigue el contador de tu aplicación.** Puedes hacer clic en las imágenes para ampliarlas.

### Elige tu idioma

Usa **↑ / ↓** para elegir **Español, English, 简体中文, 日本語, 한국어 o Français** y pulsa **Return**. La elección queda guardada. Si entras directamente en Preparar, ya tienes una elección guardada; puedes cambiarla con **S**.

![Selección inicial de idioma, con Español resaltado para confirmar con Return](docs/images/language-es.png)

### 1. Prepara los dispositivos

En **Portal**, desliza hacia la izquierda desde la esquina superior derecha para abrir el menú rápido y elige **Desconectar**. Deja desactivada la opción de poner la PS5 conectada en modo de reposo para que siga encendida. La [guía de Sony sobre Uso a distancia (en inglés)](https://www.playstation.com/en-nz/support/hardware/playstation-remote-play-on-psportal/) te ayuda a encontrar el menú.

**Mantén Portal encendido y conectado al Wi-Fi.** Solo estás terminando la sesión de juego actual. Mantén también el ordenador despierto y, si es un portátil, con la tapa abierta.

En el **ordenador**, lee los avisos amarillos y pulsa **Return** para pasar a Equipos.

![Pantalla de preparación: misma red, Portal desconectado de PS5 y Mac despierto](docs/images/prepare-es.png)

### 2. Introduce dos direcciones y mantén 65 Mbps

<a id="find-device-addresses"></a>

**Primero busca las direcciones de tu PS5 y de Portal.** Una dirección IPv4 identifica un dispositivo en la red de casa: son cuatro grupos de números separados por puntos. Los dos dispositivos tienen direcciones diferentes.

1. Abre la aplicación o página de administración que usas para el **router o Wi-Fi de casa**. El nombre depende del router o de tu proveedor de Internet.
2. Busca **Dispositivos**, **Dispositivos conectados** o **Clientes / Clients**. Abre la entrada de **PS5** y anota su **dirección IP / IPv4**. Haz lo mismo con **PlayStation Portal**.
3. Ten a mano esos dos números. Necesitas las direcciones de los dispositivos, no la del router, una dirección MAC ni el resultado de un test de velocidad. **No copies `192.168.1.20` ni `192.168.1.30` de esta guía.**

Como ejemplo con imágenes, [TP-Link Tether usa Local Device → Clients → el dispositivo (en inglés)](https://www.tp-link.com/us/support/faq/2611/). [ASUS también tiene una guía de su lista de dispositivos (en inglés)](https://www.asus.com/us/support/faq/1005513/). Si no sabes abrir la aplicación del router o identificar los dispositivos, pide esas dos direcciones locales a quien configuró tu Wi-Fi o a tu proveedor de Internet antes de continuar.

**Ahora rellena la pantalla del ordenador de arriba abajo:**

| Fila | Qué hacer antes de pulsar Return |
| --- | --- |
| **IPv4 de PS5** | Escribe la dirección de la PS5 que has encontrado. |
| **IPv4 de Portal** | Escribe la dirección de Portal que has encontrado. |
| **Interfaz LAN del Mac** — solo macOS | Normalmente puedes dejar el valor propuesto, como `en0`. Si está vacío o usas otro adaptador, [compruébalo aquí](#mac-adapter). |
| **Adaptador LAN del PC** — solo Windows | Usa **← / →** para elegir el adaptador Wi-Fi o Ethernet conectado al router de casa. |
| **Bitrate (Mbps)** | Para la primera prueba, deja **65 recomendado** seleccionado. |
| **Guardar y preparar conexión** | Pulsa Return para empezar. Mantén Portal desconectado por ahora. |

Al entrar en un campo, empezar a escribir sustituye su contenido anterior. Usa **↑** para volver si te equivocas. Las direcciones y el bitrate se guardan para la próxima vez.

![Primer uso: el campo de la PS5 está resaltado e indica dónde escribir](docs/images/devices-input-es.png)

<details>
<summary>Ver las pulsaciones y el texto animado de la recomendación de 65 Mbps</summary>

Este ejemplo introduce direcciones de muestra, conserva el adaptador y 65 Mbps, y llega al botón de inicio. La animación se repite; lo que escribas en tu ventana se mantendrá.

![Recorrido por las direcciones de PS5 y Portal, el adaptador, 65 Mbps y el botón de inicio](docs/images/devices-es.gif)

</details>

<details>
<summary>¿Cuándo probar 100 o 200 Mbps?</summary>

En la fila de bitrate, usa **← / →** o **Espacio** para elegir. Prueba **100 Mbps** después de una sesión estable a 65 Mbps. **200 Mbps** es experimental y puede aumentar los tirones. Compara la misma escena de juego; más no siempre es mejor.

</details>

### 3. Espera en el ordenador y después conecta desde Portal

**Primero, ESPERA significa que debes esperar.** Deja Portal desconectado mientras el ordenador comprueba los dispositivos y prepara la conexión.

![Pantalla ESPERA: no conectes Portal mientras se comprueban los dispositivos](docs/images/connect-wait-es.png)

**Después, LISTO / CONECTA AHORA significa que debes coger Portal.** En su pantalla de inicio de Uso a distancia, selecciona tu PS5 y conéctate como de costumbre. Tienes **120 segundos** desde que el contador del ordenador muestra **02:00**. La aplicación espera a que **tú inicies la conexión desde Portal**.

![Pantalla CONECTA AHORA: conecta Portal a PS5 durante los dos minutos del contador](docs/images/connect-ready-es.png)

Cuando Portal se conecte, déjalo conectado. Espera a la pantalla **Resultado** del ordenador antes de cerrar nada. Si se agota el tiempo, sigue las instrucciones del resultado para volver a intentarlo.

Para detener el intento antes, pulsa **Q** en el ordenador y espera al resultado. Mantén el ordenador despierto durante la restauración de la conexión.

<details>
<summary>Ver un ejemplo de conexión con la espera abreviada</summary>

Esta demo repetida pasa de ESPERA a CONECTA AHORA, las comprobaciones y el resultado correcto. Usa eventos simulados y acorta la espera. **El contador que debes seguir es el de tu aplicación.**

![Un intento simulado correcto desde la comprobación de dispositivos hasta el resultado](docs/images/connect-es.gif)

</details>

### 4. Confirma el objetivo y comprueba Portal

**Objetivo de bitrate confirmado** en verde y **`[OK]`** indican que PS5 informó del objetivo más alto. **Comprueba imagen, sonido y controles en Portal antes de jugar.** La herramienta no verifica la reproducción ni las tablas de direcciones de los dispositivos. Si la pantalla sigue negra, desconecta y vuelve a conectar normalmente sin Better Portal, y comunica el problema. Mantén el ordenador despierto hasta que termine la restauración. Pulsa **Q** para salir y, cuando aparezca `Press Enter to close`, pulsa Return y cierra la ventana.

Las imágenes y animaciones muestran una versión anterior que llamaba a este resultado **Listo para jugar**. Ese mensaje también confirmaba únicamente el objetivo.

![Resultado correcto: Listo para jugar y un enlace verde OK entre Portal y PS5](docs/images/result-success-es.png)

Un número como **63.106 Mbps** es el objetivo que ha comunicado la PS5, **no una medición del bitrate real del vídeo**. El ordenador ya no necesita retransmitir los datos de esta sesión.

**La próxima vez que desconectes o apagues Portal:** abre **Start.command** en Mac o **Start-Windows.cmd** en Windows y repite los cuatro pasos. Las direcciones guardadas aparecerán rellenas; revísalas si ha cambiado tu red.

## Si aparece otro resultado

Son **resultados alternativos**, no fases por las que debas pasar después de una sesión correcta.

| Mensaje del asistente | Qué hacer |
| --- | --- |
| **No se detectó una nueva conexión / Sin solicitud de inicio compatible** | Desconecta Portal de PS5 y pulsa **Return** para reintentar. Conecta desde Portal solo cuando vuelva a aparecer CONECTA AHORA. |
| **Objetivo más alto sin confirmar / Objetivo recibido; verificación incompleta** | Pulsa **D** para ver los detalles. Tras restaurar la red, conecta normalmente o reintenta con 65 Mbps. |
| **Intento detenido** | Lee el estado de restauración. Si ha terminado, reintenta con Return o sal con Q. |
| **Revisa la restauración de la red** | Mantén el ordenador despierto y pulsa **D** para ver los detalles. Espera a que termine la recuperación antes de otro intento. |

<details>
<summary>Ver ejemplos separados de reintento y recuperación</summary>

**Sin nueva conexión:** inicia otro intento y conecta de nuevo desde Portal después de CONECTA AHORA.

![Ejemplo de un intento terminado sin detectar una nueva conexión de Portal](docs/images/result-timeout-es.png)

**Restauración pendiente:** mantén el ordenador despierto y sigue las indicaciones de D: detalles.

![Ejemplo de restauración incompleta de la red con indicaciones para consultar los detalles](docs/images/result-recovery-es.png)

La [animación de resultados](docs/images/result-es.gif) muestra varios resultados simulados por separado para compararlos. Una sesión correcta no pasa por todos ellos.

</details>

## Cambiar el idioma durante el uso

Pulsa **S**, elige un idioma con las **flechas** y vuelve con **Enter, Esc o S**. El cambio se aplica al instante y se guarda. Esc cierra el panel sin deshacer el cambio. Los datos introducidos y el paso actual se mantienen.

Durante la conexión, el contador sigue avanzando aunque los ajustes estén abiertos. **Q** sigue deteniendo el intento. El panel se cierra cuando empieza la restauración de la red.

<details>
<summary>Ver el cambio inmediato de idioma y las distintas traducciones</summary>

![Cambio inmediato entre seis idiomas y vuelta al mismo formulario](docs/images/settings.gif)

![La misma pantalla de dispositivos en japonés, coreano, español y francés](docs/images/languages.gif)

</details>


<a id="troubleshooting-and-recovery"></a>

<a id="questions-and-fixes"></a>

## Preguntas y soluciones

**¿Problemas con la instalación, los permisos, Npcap o el adaptador en Windows?**

Consulta la [guía de solución de problemas de Windows (en inglés)](WINDOWS.md#questions-and-fixes). Los archivos `.command` y las instrucciones del adaptador del Mac que aparecen a continuación son para macOS.

<a id="macos-blocked"></a>

**macOS no abre el archivo: no puede verificar al desarrollador o Apple no puede comprobarlo.**

Después de intentar abrir el archivo descargado de este repositorio, ve a **menú Apple → Ajustes del Sistema → Privacidad y seguridad**. Busca el aviso del archivo bloqueado. Si confías en esta descarga, elige **Abrir igualmente** y confirma **Abrir**. Las [instrucciones con imágenes de Apple (en inglés)](https://support.apple.com/en-us/102445) explican estos avisos. Un aviso de que el archivo «dañará tu ordenador» es un caso diferente: detente y sigue la ayuda de Apple para ese aviso.

**Setup muestra un error de Python o de certificados en vez de «Setup complete».**

Completa los [pasos de Python para macOS](#macos-quick-start), incluido **Install Certificates.command**. Cierra la ventana del intento fallido y vuelve a abrir **Setup.command**. Si sigue fallando, copia el error cuando pidas ayuda.

**La contraseña no funciona o la cuenta no puede usar sudo.**

Usa la contraseña de inicio de sesión del Mac. Si tu cuenta no es administradora, pide a quien administra el Mac que te ayude a autorizar el inicio.

**El texto se corta o la aplicación pide una ventana más grande.**

Arrastra una esquina de Terminal para ampliarlo. La aplicación necesita al menos 72 columnas y 24 filas de texto. Vuelve a mostrarse cuando hay espacio suficiente.

**Un dispositivo no responde o la imagen da tirones.**

Mantén PS5 y Portal despiertos. Revisa las direcciones actuales y el Wi-Fi de casa. Si hay tirones, prueba 65 Mbps o desconecta Portal y vuelve a conectarlo normalmente sin ejecutar Better Portal.

**¿Se guarda mi contraseña de administrador?**

No. macOS o Windows gestiona la autorización. Reintentar dentro del mismo asistente abierto no vuelve a pedirla.

**¿Cómo pido ayuda?**

[Abre una incidencia](https://github.com/wchwawa/better-portal/issues) e indica el paso y el mensaje que aparecen, las versiones del sistema operativo de tu ordenador y de Portal, y el bitrate elegido. Oculta las direcciones de los dispositivos en las capturas antes de compartirlas. Los informes y las capturas de paquetes pueden contener información privada de la red; consérvalos en tu equipo.

<a id="terminal-help"></a>

<details>
<summary>Ayuda con Terminal en macOS: abrir la carpeta, probar la demo y resolver un archivo Python que falta</summary>

Para abrir Terminal manualmente, pulsa **Comando (⌘) + Espacio**, escribe **Terminal** y pulsa Return.

1. Escribe `cd` seguido de **un espacio**.
2. Arrastra la **carpeta better-portal-main** desde Finder hasta Terminal y pulsa Return. Así le indicas qué carpeta debe usar.
3. Copia **un comando cada vez** de los siguientes, pégalo en Terminal y pulsa Return. Copia solo el texto del comando.

Si Start no encuentra `.venv/bin/python`, ejecuta primero la instalación desde esa carpeta:

```sh
./Setup.command
```

Después, para preparar una sesión real:

```sh
./Start.command
```

Para **ver solo la demo**, después de instalar:

```sh
.venv/bin/python portal_tui.py --demo
```

Para **ver la demo sin animaciones**:

```sh
.venv/bin/python portal_tui.py --demo --no-animations
```

Los dos comandos de demo simulan una conexión sin usar tus dispositivos. No necesitan contraseña de administrador, no cambian la red ni guardan ajustes. Cierra la demo antes de abrir Start.command para una sesión real.

</details>

<a id="mac-adapter"></a>

<details>
<summary>La interfaz LAN del Mac está vacía o uso un adaptador USB / Ethernet</summary>

La interfaz es un nombre como `en0`, no el nombre del Wi-Fi ni una dirección IP. Abre Terminal como se explica arriba y ejecuta:

```sh
networksetup -listallhardwareports
```

Para Wi-Fi, busca la sección **Hardware Port: Wi-Fi** y usa el nombre que aparece junto a **Device:**. Para una conexión por cable, busca la sección del adaptador Ethernet conectado. Introduce ese nombre en Better Portal. Si no sabes qué adaptador estás usando, indícalo al pedir ayuda.

</details>

<details>
<summary>¿Ya usas Git y Terminal en Mac?</summary>

```sh
git clone https://github.com/wchwawa/better-portal.git
cd better-portal
./Setup.command
./Start.command
```

</details>

**¿Usas Linux?** Consulta la [guía de Linux / configuración automática original](https://github.com/atameric/ps5-portal-high-bitrate/blob/main/AUTOMATION.md).
