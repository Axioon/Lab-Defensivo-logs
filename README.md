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

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
```

Agregar el repositorio oficial de Docker:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
```

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

```bash
sudo systemctl enable --now docker
```

Comprobar:

```bash
sudo docker --version && sudo docker compose version
```

## 4. Clonar **este** repositorio

```bash
git clone https://github.com/Axioon/Lab-Defensivo-logs.git
```

```bash
cd Lab-Defensivo-logs
```

Verificar archivos:

```bash
ls -la && ls -la webapp nginx
```

Este repositorio incluye los archivos `compose.local.yaml`, `webapp/app.py`, `webapp/Dockerfile`, `webapp/requirements.txt` y `nginx/default.conf`.

## 5. Adaptar Docker Compose para AWS

El archivo **`compose.local.yaml`** fue probado con Docker Desktop y publica **`8080:80`** para pruebas locales. En AWS crearemos una copia con el puerto **80:80**:

```bash
cp compose.local.yaml compose.ec2.yaml
```

```bash
sed -i 's/"8080:80"/"80:80"/' compose.ec2.yaml
```

Confirmar que la línea se reemplazó:

```bash
grep -A 2 'ports:' compose.ec2.yaml
```

La salida debe mostrar `- "80:80"`. **Si aún indica `8080:80`, no continúes:** edita `compose.ec2.yaml` y corrige el mapeo.

Crear una clave aleatoria **únicamente en la copia para AWS** (no usar la clave de ejemplo):

```bash
python3 -c 'import secrets,pathlib; p=pathlib.Path("compose.ec2.yaml"); s=p.read_text(); s=s.replace("clave-temporal-laboratorio-local",secrets.token_hex(32)); p.write_text(s)'
```

No publicar `compose.ec2.yaml`, pues contiene la clave generada. Excluirlo del repositorio local:

```bash
printf '\ncompose.ec2.yaml\n' >> .git/info/exclude
```

Validar:

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

## 6. Construir e iniciar la aplicación

```bash
sudo docker compose -f compose.ec2.yaml up -d --build
```

```bash
sudo docker compose -f compose.ec2.yaml ps
```

Deben aparecer los dos servicios: **nginx** y **webapp**.

Probar desde la propia EC2:

```bash
curl -i http://127.0.0.1/
```

No debe devolver `502 Bad Gateway`. Si aparece ese error, consultar los logs de la aplicación antes de modificar archivos.

## 7. Acceso de los alumnos

Desde un navegador y **desde una IP autorizada por el Security Group**:

```text
http://IP_PUBLICA_DE_LA_EC2
```

Usar únicamente el sitio y las pruebas previstas por el docente (ejemplos: autenticaciones correctas e incorrectas, rutas inexistentes y solicitudes sospechosas de laboratorio). No realizar pruebas contra sistemas externos ni usar contraseñas personales.

## 8. Ver los eventos y logs

Ver todos los eventos en tiempo real:

```bash
sudo docker compose -f compose.ec2.yaml logs -f
```

Solo Nginx (solicitudes HTTP y errores):

```bash
sudo docker compose -f compose.ec2.yaml logs -f nginx
```

Solo la WebApp (eventos de la aplicación):

```bash
sudo docker compose -f compose.ec2.yaml logs -f webapp
```

También se puede generar tráfico de ejemplo desde la propia EC2:

```bash
curl -i http://127.0.0.1/no-existe
```

Los mensajes exactos dependen del código y las rutas de la aplicación. Para dejar de seguir los logs, presionar **Ctrl+C** (no detiene los contenedores).

## 9. Comandos operativos

| Acción | Comando |
|---|---|
| Ver estado | `sudo docker compose -f compose.ec2.yaml ps` |
| Ver logs | `sudo docker compose -f compose.ec2.yaml logs -f` |
| Reiniciar servicios | `sudo docker compose -f compose.ec2.yaml restart` |
| Detener contenedores | `sudo docker compose -f compose.ec2.yaml down` |
| Volver a iniciarlos | `sudo docker compose -f compose.ec2.yaml up -d` |
| Reconstruir | `sudo docker compose -f compose.ec2.yaml up -d --build` |

## 10. Solución de problemas

**Error 502 / WebApp no inicia:**

```bash
sudo docker compose -f compose.ec2.yaml ps
```

```bash
sudo docker compose -f compose.ec2.yaml logs --tail 80 webapp
```

**No abre desde Internet:** revisar IP pública, mapeo `80:80`, Security Group (TCP 80 desde IP autorizada) y firewall de Ubuntu.

**Validación de Compose:**

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

**Puerto 80 ocupado:**

```bash
sudo ss -ltnp | grep ':80 '
```

## 11. Finalizar la práctica y controlar costos

```bash
sudo docker compose -f compose.ec2.yaml down
```

Cerrar las reglas de entrada de los alumnos y detener la EC2 desde AWS cuando termine la práctica. Detener EC2 no elimina todos los posibles cargos asociados (por ejemplo, almacenamiento).

## Referencias oficiales

- [Instalación Docker Engine en Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose](https://docs.docker.com/compose/)
- [AWS EC2 con Session Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-with-systems-manager-session-manager.html)

---

**Alcance:** despliegue de **una sola EC2-App** para registrar eventos localmente con Docker. No incluye EC2 colectora ni envío a Syslog; esa integración, si se requiere, se documentará por separado.
