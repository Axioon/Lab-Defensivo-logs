[README_LAB_CIBERSEGURIDAD.md](https://github.com/user-attachments/files/35209934/README_LAB_CIBERSEGURIDAD.md)
# Laboratorio de Ciberseguridad Defensiva — Docker, Nginx y Flask

Laboratorio educativo para que estudiantes autorizados accedan desde Internet a una WebApp de práctica en AWS, generen eventos de seguridad y los observen centralizados en una segunda EC2 con Rsyslog. Incluye Flask, Nginx y Docker Compose.

> **Seguridad:** Este laboratorio contiene funciones intencionalmente vulnerables para enseñanza. Úsalo solo en una cuenta y red de pruebas autorizadas. No emplees credenciales reales. Restringe el acceso por dirección IP y apaga la instancia fuera de clases. No lo publiques abierto a todo Internet.

## 1. Arquitectura

- **Nginx:** recibe las conexiones HTTP y registra solicitudes.
- **WebApp Flask:** presenta la interfaz del laboratorio y genera eventos de autenticación.
- **Docker Compose:** construye e inicia ambos servicios.
- **Colector Syslog (objetivo del laboratorio):** una segunda EC2 recibe los logs de Nginx y Flask mediante TCP 514 por red privada. Para pruebas previas, la WebApp puede iniciarse sin colector.

## 2. Requisitos de AWS EC2

Crear **dos instancias** en la misma VPC (o redes privadas con conectividad entre sí):

- **EC2-App:** ejecuta Docker, Nginx y Flask; publica el sitio hacia los alumnos autorizados.
- **EC2-Colector:** ejecuta Rsyslog y recibe registros mediante TCP 514 desde la EC2-App, usando la IP privada.

Configuración sugerida para cada instancia:

- **Ubuntu Server 22.04 o 24.04 LTS**, arquitectura x86_64.
- Tamaño sugerido para demostración inicial: **t3.small o t3.medium** (ajustar según número de alumnos).
- Almacenamiento sugerido: **20 GB gp3**.
- Salida a Internet para instalar paquetes y descargar imágenes.
- **Security Group EC2-App:** permitir TCP 80 solo desde las IP públicas de los alumnos/profesor o la salida de una VPN de clase. No abrir TCP 5000.
- **Security Group EC2-Colector:** permitir TCP 514 solo **desde el Security Group de EC2-App** (o su IP privada), jamás desde Internet. No asignar IP pública al colector si no la necesita.
- Para administrarla con **AWS Systems Manager Session Manager**, contar con SSM Agent, conectividad a los endpoints de Systems Manager y un rol IAM con los permisos correspondientes (por ejemplo, `AmazonSSMManagedInstanceCore`). Si se utiliza Session Manager, no hace falta abrir SSH/22.

> El laboratorio usa HTTP sin TLS y tiene vulnerabilidades deliberadas. Para una clase remota, se recomienda acceder mediante una VPN o un entorno de prácticas aislado, en vez de exponer la aplicación libremente a Internet.

## 3. Conectarse a la EC2

En la consola AWS, seleccionar la instancia y abrir **Connect > Session Manager**. Los siguientes comandos se ejecutan **en Ubuntu dentro de la EC2**, no en PowerShell de Windows.

## 4. Instalar Git y Docker

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
```

La instalación recomendada de Docker usa su repositorio oficial:

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

Verificar:

```bash
sudo docker --version && sudo docker compose version
```

## 5. Descargar el proyecto desde GitHub

Sustituye `USUARIO/REPOSITORIO` por la URL **real** de este repositorio. Si es privado, Git solicitará autenticación.

```bash
git clone https://github.com/USUARIO/REPOSITORIO.git
```

```bash
cd REPOSITORIO
```

Verificar que existan `webapp/app.py`, `webapp/Dockerfile`, `webapp/requirements.txt`, `nginx/default.conf` y `compose.local.yaml`:

```bash
ls -la && ls -la webapp nginx
```

## 6. Preparar la configuración para EC2

**No ejecutar el antiguo `docker-compose.yml` directamente:** esa versión podría exigir variables o un colector Syslog de la implementación original.

Crear una **copia** de la configuración local, sin modificarla:

```bash
cp compose.local.yaml compose.ec2.yaml
```

El archivo local publica `127.0.0.1:8080:80`. En la EC2, cambiar esa asignación por `80:80`, de modo que Nginx escuche en el puerto 80 de la instancia. La protección del acceso externo se realiza con el Security Group:

```bash
sed -i 's/127\.0\.0\.1:8080:80/80:80/' compose.ec2.yaml
```

Verificar que el puerto esté correctamente definido:

```bash
grep -A 2 'ports:' compose.ec2.yaml
```

La salida debe incluir `80:80` (con comillas o en formato equivalente). Si no aparece, **editar `compose.ec2.yaml` y corregir el puerto antes de continuar**.

Para no utilizar una clave de sesión compartida, reemplazar la clave temporal de ejemplo por un valor aleatorio:

```bash
python3 -c 'import secrets,pathlib; p=pathlib.Path("compose.ec2.yaml"); s=p.read_text(); s=s.replace("clave-temporal-laboratorio-local",secrets.token_hex(32)); p.write_text(s)'
```

> **No subir `compose.ec2.yaml` a GitHub**, porque ahora contiene una clave específica de la instancia. Agrégalo a `.gitignore` si vas a gestionar cambios con Git.

```bash
printf '\ncompose.ec2.yaml\n' >> .git/info/exclude
```

Validar la configuración (evita compartir su salida públicamente porque puede mostrar la clave):

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

## 7. Construir e iniciar

```bash
sudo docker compose -f compose.ec2.yaml up -d --build
```

Comprobar el estado:

```bash
sudo docker compose -f compose.ec2.yaml ps
```

Probar localmente desde la EC2:

```bash
curl -I http://127.0.0.1
```

> Si la app no admite `HEAD`, probar `curl -i http://127.0.0.1/`. Debe devolver contenido de la aplicación, no un `502 Bad Gateway`.

## 8. Acceder desde el navegador

Abrir `http://IP_PUBLICA_EC2` **desde una IP incluida en el Security Group**. La instancia necesita una IP pública o conectividad privada adecuada (VPN, túnel, etc.).

No publicar el puerto 5000 de Flask; Nginx es el único punto de entrada.

## 9. Verificar logs

Identificar los contenedores:

```bash
sudo docker compose -f compose.ec2.yaml ps
```

Ver ambos flujos de logs en tiempo real:

```bash
sudo docker compose -f compose.ec2.yaml logs -f
```

Ver solo la aplicación:

```bash
sudo docker compose -f compose.ec2.yaml logs -f webapp
```

Ver solo Nginx:

```bash
sudo docker compose -f compose.ec2.yaml logs -f nginx
```

Generar tráfico de prueba desde la propia EC2:

```bash
curl -i http://127.0.0.1/
```

```bash
curl -i http://127.0.0.1/no-existe
```

Las solicitudes deben aparecer en los registros de Nginx. Las pruebas de autenticación se realizan desde el formulario del laboratorio.

## 10. Comandos de operación

| Acción | Comando |
|---|---|
| Estado | `sudo docker compose -f compose.ec2.yaml ps` |
| Ver logs | `sudo docker compose -f compose.ec2.yaml logs -f` |
| Reiniciar servicios | `sudo docker compose -f compose.ec2.yaml restart` |
| Detener y retirar contenedores | `sudo docker compose -f compose.ec2.yaml down` |
| Iniciar nuevamente | `sudo docker compose -f compose.ec2.yaml up -d` |
| Reconstruir tras actualizar archivos | `sudo docker compose -f compose.ec2.yaml up -d --build` |

## 11. Solución de problemas

**Error 502 Bad Gateway:** comprobar que la WebApp esté activa y revisar sus registros:

```bash
sudo docker compose -f compose.ec2.yaml ps
```

```bash
sudo docker compose -f compose.ec2.yaml logs --tail 80 webapp
```

**No abre desde el navegador:** comprobar que Nginx publica TCP 80, que el Security Group permite tu IP, y que existe conectividad hacia la instancia.

**Error de configuración de Compose:**

```bash
sudo docker compose -f compose.ec2.yaml config --quiet
```

**Puerto ocupado:**

```bash
sudo ss -ltnp | grep ':80 '
```

## 12. Configurar EC2-Colector (Rsyslog) — obligatorio para centralizar eventos

Conectarse por SSM a **EC2-Colector** (Ubuntu). Configurar una carpeta separada para las fuentes:

```bash
sudo apt-get update && sudo apt-get install -y rsyslog
```

```bash
sudo install -d -o syslog -g adm -m 0750 /var/log/lab
```

Crear una configuración de recepción TCP y clasificación por etiqueta:

```bash
sudo tee /etc/rsyslog.d/30-lab-docker.conf > /dev/null <<'EOF'
module(load="imtcp")
input(type="imtcp" port="514")

if ($syslogtag startswith "lab-nginx") then {
    action(type="omfile" file="/var/log/lab/nginx.log")
    stop
}
if ($syslogtag startswith "lab-webapp") then {
    action(type="omfile" file="/var/log/lab/webapp.log")
    stop
}
EOF
```

Validar, iniciar y comprobar recepción:

```bash
sudo rsyslogd -N1 && sudo systemctl enable --now rsyslog && sudo systemctl restart rsyslog
```

```bash
sudo ss -ltnp | grep ':514 '
```

**Red:** en el Security Group del colector, autorizar TCP 514 **solo desde EC2-App**. Anotar la **IP privada actual** de EC2-Colector. Nunca usar la dirección histórica de otro entorno sin comprobarla.

## 13. Activar el envío desde EC2-App

Conectarse por SSM a **EC2-App**. Los pasos 1 a 11 deben haberse completado y la WebApp debe funcionar localmente. Cambiar `IP_PRIVADA_DEL_COLECTOR` por la IP privada real (por ejemplo, `10.0.2.15`; ese valor es solo ilustrativo).

Antes de configurar el driver de Docker, verificar la conectividad por TCP:

```bash
COLLECTOR_IP=IP_PRIVADA_DEL_COLECTOR
```

```bash
COLLECTOR_IP="$COLLECTOR_IP" python3 -c 'import os,socket; socket.create_connection((os.environ["COLLECTOR_IP"],514),timeout=5).close(); print("TCP 514 accesible")'
```

Crear un archivo de Compose adicional **solo en esta EC2**, que cambia el driver de logs y conserva los demás parámetros de `compose.ec2.yaml`:

```bash
cat > compose.syslog.yaml <<EOF
services:
  nginx:
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://${COLLECTOR_IP}:514"
        syslog-format: "rfc5424"
        tag: "lab-nginx"
  webapp:
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://${COLLECTOR_IP}:514"
        syslog-format: "rfc5424"
        tag: "lab-webapp"
EOF
```

Verificar la configuración sin mostrarla a terceros porque puede incluir variables sensibles:

```bash
sudo docker compose -f compose.ec2.yaml -f compose.syslog.yaml config --quiet
```

**Recrear** los contenedores para que Docker aplique el cambio de driver:

```bash
sudo docker compose -f compose.ec2.yaml -f compose.syslog.yaml up -d --build --force-recreate
```

```bash
sudo docker compose -f compose.ec2.yaml -f compose.syslog.yaml ps
```

> Nota: con el driver `syslog`, la fuente principal de registros pasa a ser el colector; `docker compose logs` puede no comportarse igual que usando `json-file`. Para depurar fallos, volver temporalmente a `compose.ec2.yaml` y consultar logs locales.

## 14. Comprobar que llegan eventos anómalos

Desde el navegador de un alumno autorizado, abrir `http://IP_PUBLICA_EC2` y realizar exclusivamente las pruebas previstas por el docente: inicio de sesión válido, contraseña incorrecta, URL inexistente, acceso denegado y solicitud sospechosa de laboratorio. **No utilizar credenciales reales ni probar sistemas fuera del laboratorio.**

En **EC2-Colector**, seguir los logs en dos terminales SSM:

```bash
sudo tail -F /var/log/lab/nginx.log
```

```bash
sudo tail -F /var/log/lab/webapp.log
```

Si los archivos no aparecen, revisar primero Security Groups, conectividad TCP 514 y el servicio Rsyslog; luego verificar las etiquetas `lab-nginx` y `lab-webapp` en los mensajes. Los registros de inicio de sesión dependen del comportamiento de la aplicación original y de las rutas efectivamente ejecutadas.

**Alcance:** los logs y las etiquetas son evidencia para análisis; no implican detección automática de amenazas ni sustituyen un SIEM. Wazuh puede añadirse posteriormente.

## 15. Publicación segura para una clase

- Publicar solo TCP 80 a las IP autorizadas de los alumnos o mediante VPN; **nunca** abrir el laboratorio deliberadamente vulnerable a `0.0.0.0/0`.
- Publicar un sitio HTTP solo para pruebas desechables y sin datos reales; HTTP no protege contraseñas de tránsito. Si la clase no es en una red de confianza, preferir HTTPS o VPN.
- Mantener EC2-Colector en red privada, sin exponer TCP 514 públicamente.
- No subir `.env`, secretos, contraseñas reales, archivos `compose.ec2.yaml` ni `compose.syslog.yaml` ya personalizados a GitHub. Revisar `webapp/app.py` antes de publicar, pues puede contener credenciales de demostración o configuración específica.
- Al finalizar la clase, restringir nuevamente el Security Group y detener los recursos.

## 16. Apagar y limpiar

Al terminar una clase con Syslog activado:

```bash
sudo docker compose -f compose.ec2.yaml -f compose.syslog.yaml down
```

Detener la EC2 desde la consola AWS para evitar cargos innecesarios. Si el laboratorio ya no se necesita, eliminar también sus recursos, teniendo presente que detener EC2 no elimina todos los cargos asociados.

## Referencias oficiales

- [Docker Engine en Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose en Linux](https://docs.docker.com/compose/install/linux/)
- [Conectar a EC2 mediante Session Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-with-systems-manager-session-manager.html)
