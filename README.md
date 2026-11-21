# LAB Defensivo Logs — Ciberseguridad Defensiva

Laboratorio educativo para desplegar **una aplicación web en una sola instancia AWS EC2** con Docker, Nginx y Flask. Los alumnos autorizados acceden a la WebApp, generan eventos de autenticación y tráfico HTTP de prueba, y el docente observa los registros **localmente desde Docker**, sin otra EC2 ni colector Syslog.

> **Uso exclusivo en entorno autorizado:** la aplicación original contiene funciones intencionalmente vulnerables. Utilizar solo cuentas y datos de prueba, restringir el acceso a las IP de los participantes, mantenerla aislada de sistemas reales y apagarla al terminar. No dejarla abierta indiscriminadamente a Internet.

## Arquitectura

```text
Alumnos autorizados (navegador)
           |
        HTTP / 80
           |
     AWS EC2 Ubuntu
           |
        Nginx (Docker) ----> logs HTTP
           |
       WebApp Flask --------> logs aplicación
           |
    docker compose logs -f
```

**No se necesita Rsyslog, colector ni segunda instancia EC2.**

## 1. Crear y preparar la EC2

- Imagen: **Ubuntu Server 22.04 o 24.04 LTS**, x86_64.
- Para una prueba pequeña, sugerencia inicial: **t3.small o t3.medium**; ajustar según alumnos y carga.
- Almacenamiento de referencia: **20 GB gp3**.
- La instancia necesita salida a Internet para obtener paquetes e imágenes Docker.
- Para acceso web desde fuera de AWS, asignar conectividad/IP pública. Si la IP cambia al reiniciar, actualizar el enlace de la clase.
- **Security Group:** permitir entrada **TCP 80 únicamente desde las IP públicas autorizadas** del profesor y alumnos (o desde la salida de la VPN del curso). No exponer TCP 5000.
- Administración: preferir **AWS Systems Manager Session Manager** con rol IAM, agente SSM y conectividad configurados. Con SSM no es necesario abrir el puerto SSH/22.

> HTTP no cifra las credenciales. Usar solo credenciales ficticias y preferir una VPN/HTTPS si el escenario lo permite. No habilitar `0.0.0.0/0` para esta aplicación intencionalmente vulnerable.

## 2. Conectarse a Ubuntu

En la consola de AWS: **EC2 → Instances → seleccionar instancia → Connect → Session Manager**.

Todos los comandos siguientes se ejecutan **dentro de la terminal Ubuntu de la EC2**, no en PowerShell de Windows.

## 3. Instalar Git y Docker Compose

**Conceptos:** Git descarga el proyecto; Docker ejecuta programas aislados en contenedores; Docker Compose define cómo se ejecutan juntos Nginx (servidor web) y Flask (aplicación). Ejecuta los comandos en orden, **uno a uno**, y comprueba que no aparezcan errores.

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
```

**¿Para qué sirve?** Actualiza la lista de paquetes disponibles e instala Git (descarga el código), curl (descarga archivos por HTTP/HTTPS) y certificados CA (verifican conexiones HTTPS). `sudo` concede permisos administrativos, `&&` ejecuta el segundo comando solo si el primero funcionó y `-y` acepta la instalación.

Agregar el repositorio oficial de Docker:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

**¿Para qué sirve?** Crea la carpeta donde Ubuntu almacenará claves de confianza de repositorios. `-d` indica directorio y `-m 0755` configura sus permisos.

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
```

**¿Para qué sirve?** Descarga la clave pública de firma del repositorio oficial de Docker. `-f` falla ante errores HTTP, `-sS` reduce el ruido pero muestra errores, `-L` sigue redirecciones y `-o` guarda el archivo en la ruta indicada.

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

**¿Para qué sirve?** Da permiso de lectura de esa clave a todos los usuarios, para que el gestor de paquetes pueda comprobar firmas.

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

**¿Para qué sirve?** Registra el repositorio oficial de Docker en APT. Detecta automáticamente la arquitectura y versión de Ubuntu; `signed-by` indica la clave de verificación; `tee` guarda la entrada con permisos administrativos. No instala Docker todavía.

```bash
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**¿Para qué sirve?** Actualiza el catálogo de paquetes e instala el motor de Docker, su cliente de comandos, containerd, Buildx y el complemento Docker Compose. **Resultado esperado:** Ubuntu ya puede construir y ejecutar contenedores.

```bash
sudo systemctl enable --now docker
```

**¿Para qué sirve?** Activa el servicio Docker inmediatamente (`--now`) y configura su inicio automático al reiniciar la EC2 (`enable`).

Comprobar:

```bash
sudo docker --version && sudo docker compose version
```

**¿Para qué sirve?** Confirma que el cliente Docker y Docker Compose están instalados. Si ambos muestran una versión, se puede continuar. Esto no verifica todavía que los contenedores estén funcionando.

## 4. Clonar **este** repositorio

```bash
git clone https://github.com/Axioon/Lab-Defensivo-logs.git
```

**¿Para qué sirve?** Descarga una copia del repositorio del laboratorio desde GitHub, incluidos el código de Flask y los archivos de configuración de Nginx y Docker. **Resultado esperado:** aparece una carpeta `Lab-Defensivo-logs`.

```bash
cd Lab-Defensivo-logs
```

**¿Para qué sirve?** Cambia la ubicación de trabajo de la terminal a la carpeta clonada. Los comandos posteriores buscan allí los archivos de Docker Compose.

Verificar archivos:

```bash
ls -la && ls -la webapp nginx
```

**¿Para qué sirve?** Lista archivos, incluidos los ocultos (`-a`), y muestra sus detalles (`-l`). Comprueba que existan las carpetas `webapp` y `nginx` antes de construir.

Este repositorio incluye los archivos `compose.local.yaml`, `webapp/app.py`, `webapp/Dockerfile`, `webapp/requirements.txt` y `nginx/default.conf`.

## 5. Adaptar Docker Compose para AWS

El archivo **`compose.local.yaml`** fue probado con Docker Desktop y publica **`8080:80`** para pruebas locales. En AWS crearemos una copia con el puerto **80:80**:

```bash
cp compose.local.yaml compose.ec2.yaml
```

**¿Para qué sirve?** Duplica la configuración local probada, creando una copia exclusiva para la EC2. Así no se altera `compose.local.yaml` del repositorio.

```bash
sed -i 's/"8080:80"/"80:80"/' compose.ec2.yaml
```

**¿Para qué sirve?** Reemplaza el mapeo de puerto del equipo local (`8080` del anfitrión → `80` del contenedor) por el de AWS (`80` del anfitrión → `80` del contenedor). `-i` modifica el archivo. **Esto permite que Nginx reciba conexiones por el puerto público 80**, sujeto a las reglas del Security Group.

Confirmar que la línea se reemplazó:

```bash
grep -A 2 'ports:' compose.ec2.yaml
```

**¿Para qué sirve?** Busca la sección `ports:` y muestra las dos líneas siguientes (`-A 2`) para verificar visualmente el mapeo. Debe verse `"80:80"`.

La salida debe mostrar `- "80:80"`. **Si aún indica `8080:80`, no continúes:** edita `compose.ec2.yaml` y corrige el mapeo.

Crear una clave aleatoria **únicamente en la copia para AWS** (no usar la clave de ejemplo):

```bash
python3 -c 'import secrets,pathlib; p=pathlib.Path("compose.ec2.yaml"); s=p.read_text(); s=s.replace("clave-temporal-laboratorio-local",secrets.token_hex(32)); p.write_text(s)'
```

**¿Para qué sirve?** Usa Python para sustituir la clave temporal de ejemplo por 32 bytes aleatorios representados en hexadecimal. Es una clave diferente para cada despliegue. **No muestres ni publiques su valor**; si se usa para sesiones, evita compartirla con otras instalaciones.

No publicar `compose.ec2.yaml`, pues contiene la clave generada. Excluirlo del repositorio local:

```bash
printf '\ncompose.ec2.yaml\n' >> .git/info/exclude
```

**¿Para qué sirve?** Agrega `compose.ec2.yaml` a las exclusiones locales de Git (`.git/info/exclude`). Así el archivo personalizado que puede contener una clave no se incorpora por accidente a un commit. Esta exclusión solo afecta a esa copia local.

Validar:

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

**¿Para qué sirve?** Valida que Docker Compose pueda interpretar el archivo. `-f` selecciona nuestra configuración AWS y `--quiet` evita imprimir valores como la clave. **Resultado esperado:** termina sin errores ni salida.

## 6. Construir e iniciar la aplicación

```bash
sudo docker compose -f compose.ec2.yaml up -d --build
```

**¿Para qué sirve?** Construye la imagen de Flask cuando es necesario (`--build`), descarga la de Nginx, crea red y contenedores, e inicia los servicios en segundo plano (`-d`).

```bash
sudo docker compose -f compose.ec2.yaml ps
```

**¿Para qué sirve?** Muestra los servicios y su estado. **Resultado esperado:** `nginx` y `webapp` en ejecución. Que aparezcan iniciados no garantiza por sí solo que la página responda.

Deben aparecer los dos servicios: **nginx** y **webapp**.

Probar desde la propia EC2:

```bash
curl -i http://127.0.0.1/
```

**¿Para qué sirve?** Hace una solicitud HTTP desde la propia EC2 hacia Nginx y muestra encabezados y cuerpo (`-i`). Prueba la ruta Nginx → Flask sin depender de Internet ni del Security Group. Debes recibir una respuesta de la aplicación, no un error `502`.

No debe devolver `502 Bad Gateway`. Si aparece ese error, consultar los logs de la aplicación antes de modificar archivos.

## 7. Acceso de los alumnos

Desde un navegador y **desde una IP autorizada por el Security Group**:

```text
http://IP_PUBLICA_DE_LA_EC2
```

Usar únicamente el sitio y las pruebas previstas por el docente (ejemplos: autenticaciones correctas e incorrectas, rutas inexistentes y solicitudes sospechosas de laboratorio). No realizar pruebas contra sistemas externos ni usar contraseñas personales.

## 8. Ver los eventos y logs

**¿Qué observar?** Nginx registra solicitudes y respuestas HTTP. La WebApp puede generar mensajes de autenticación y de otras actividades previstas por el laboratorio. **Un log no equivale automáticamente a una alerta de seguridad**: hay que interpretar el evento, su contexto y su código de respuesta.

Ver todos los eventos en tiempo real:

```bash
sudo docker compose -f compose.ec2.yaml logs -f
```

**¿Para qué sirve?** Muestra en tiempo real los registros de **ambos** contenedores. `-f` significa *follow*: sigue imprimiendo eventos nuevos hasta que presiones Ctrl+C.

Solo Nginx (solicitudes HTTP y errores):

```bash
sudo docker compose -f compose.ec2.yaml logs -f nginx
```

**¿Para qué sirve?** Filtra los registros al contenedor `nginx`, útil para observar solicitudes HTTP, rutas visitadas y códigos de respuesta.

Solo la WebApp (eventos de la aplicación):

```bash
sudo docker compose -f compose.ec2.yaml logs -f webapp
```

**¿Para qué sirve?** Muestra los registros de Flask/Gunicorn, útiles para observar los mensajes que emite la aplicación y sus errores.

También se puede generar tráfico de ejemplo desde la propia EC2:

```bash
curl -i http://127.0.0.1/no-existe
```

**¿Para qué sirve?** Solicita una ruta que probablemente no existe para generar un evento HTTP de prueba, normalmente `404`. Revisa el código de respuesta y su aparición en los logs de Nginx.

Los mensajes exactos dependen del código y las rutas de la aplicación. Para dejar de seguir los logs, presionar **Ctrl+C** (no detiene los contenedores).

## 9. Comandos operativos

Esta tabla sirve como **resumen rápido** después de comprender la instalación. `restart` reinicia servicios existentes; `down` retira los contenedores; `up -d` vuelve a levantarlos; `--build` vuelve a construir las imágenes si cambió el código.

| Acción | Comando |
|---|---|
| Ver estado | `sudo docker compose -f compose.ec2.yaml ps` |
| Ver logs | `sudo docker compose -f compose.ec2.yaml logs -f` |
| Reiniciar servicios | `sudo docker compose -f compose.ec2.yaml restart` |
| Detener contenedores | `sudo docker compose -f compose.ec2.yaml down` |
| Volver a iniciarlos | `sudo docker compose -f compose.ec2.yaml up -d` |
| Reconstruir | `sudo docker compose -f compose.ec2.yaml up -d --build` |

## 10. Solución de problemas

El objetivo del diagnóstico es **localizar la causa antes de modificar el código**. Primero revisar el estado (`ps`), después los logs de `webapp` y finalmente la configuración o conectividad.

**Error 502 / WebApp no inicia:**

```bash
sudo docker compose -f compose.ec2.yaml ps
```

```bash
sudo docker compose -f compose.ec2.yaml logs --tail 80 webapp
```

**¿Para qué sirve?** Muestra únicamente las 80 últimas líneas de la aplicación. Es especialmente útil cuando Flask no inicia o Nginx devuelve un `502`.

**No abre desde Internet:** revisar IP pública, mapeo `80:80`, Security Group (TCP 80 desde IP autorizada) y firewall de Ubuntu.

**Validación de Compose:**

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

**Puerto 80 ocupado:**

```bash
sudo ss -ltnp | grep ':80 '
```

**¿Para qué sirve?** Identifica procesos con sockets TCP a la escucha (`-ltnp`) y filtra el puerto 80. Ayuda a diagnosticar conflictos con otros servicios.

## 11. Finalizar la práctica y controlar costos

```bash
sudo docker compose -f compose.ec2.yaml down
```

**¿Para qué sirve?** Detiene y elimina los contenedores y la red creada por ese proyecto Compose. No borra el repositorio, ni necesariamente las imágenes o los volúmenes persistentes. Para evitar cargos de AWS también debes detener o eliminar la EC2 según corresponda.

Cerrar las reglas de entrada de los alumnos y detener la EC2 desde AWS cuando termine la práctica. Detener EC2 no elimina todos los posibles cargos asociados (por ejemplo, almacenamiento).

## Referencias oficiales

- [Instalación Docker Engine en Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose](https://docs.docker.com/compose/)
- [AWS EC2 con Session Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-with-systems-manager-session-manager.html)

---

**Alcance:** despliegue de **una sola EC2-App** para registrar eventos localmente con Docker. No incluye EC2 colectora ni envío a Syslog; esa integración, si se requiere, se documentará por separado.
