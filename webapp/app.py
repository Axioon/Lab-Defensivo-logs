from flask import Flask, request, redirect, session, render_template_string, abort
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import logging
import os

app = Flask(__name__)
app.secret_key = os.environ["LAB_SECRET_KEY"]
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

DB = "/tmp/laboratorio.db"

BRAND_NAME = "Ricardo Moena"
BRAND_GITHUB = "Axioon"
BRAND_LINK = "https://github.com/Axioon"
BRAND_AVATAR = "https://github.com/Axioon.png"

def conexion():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar():
    with conexion() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                usuario TEXT,
                password TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY,
                nombre TEXT,
                descripcion TEXT
            )
        """)
        if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO usuarios(usuario,password) VALUES (?,?)",
                [
                    ("alumno", "Laboratorio2026!"),
                    ("operador", "Demo2026!")
                ]
            )
        if db.execute("SELECT COUNT(*) FROM documentos").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO documentos(nombre,descripcion) VALUES (?,?)",
                [
                    ("Manual de seguridad", "Documento académico"),
                    ("Inventario de activos", "Inventario ficticio"),
                    ("Política de acceso", "Política de laboratorio")
                ]
            )

inicializar()

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LAB - Ciberseguridad Defensiva</title>
<style>
* { box-sizing:border-box; }
body {
    background:#0f172a;
    color:#e2e8f0;
    font-family:Arial,sans-serif;
    margin:0;
}
header {
    background:#1e293b;
    padding:22px 30px;
    border-bottom:2px solid #0284c7;
}
h1 { color:#38bdf8; margin:0; font-size:24px; }
h2 { color:#38bdf8; }
.brand-box {
    display:flex;
    align-items:center;
    gap:14px;
    padding:14px;
    border:1px solid #334155;
    border-radius:10px;
    background:#0f172a;
    margin-bottom:18px;
}
.brand-box img {
    width:58px;
    height:58px;
    border-radius:50%;
    object-fit:cover;
    border:2px solid #38bdf8;
}
.brand-meta strong {
    display:block;
    font-size:18px;
    color:#e2e8f0;
}
.brand-meta a {
    color:#38bdf8;
    text-decoration:none;
    font-size:14px;
}
.brand-meta a:hover {
    text-decoration:underline;
}
main { max-width:950px; margin:35px auto; padding:20px; }
.panel {
    background:#1e293b;
    padding:28px;
    border-radius:12px;
    margin-bottom:20px;
}
.grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    gap:15px;
}
.card {
    display:block;
    background:#273449;
    padding:25px;
    border-radius:10px;
    color:white;
    text-decoration:none;
    border:1px solid #475569;
}
.card:hover { border-color:#38bdf8; background:#334155; }
a { color:#38bdf8; }
nav a { margin-right:18px; }
input {
    width:100%;
    padding:12px;
    margin:8px 0;
    background:#0f172a;
    color:white;
    border:1px solid #64748b;
    border-radius:6px;
}
button {
    background:#0284c7;
    color:white;
    padding:12px 20px;
    border:0;
    border-radius:6px;
    cursor:pointer;
}
.error { color:#f87171; }
table { width:100%; border-collapse:collapse; }
td,th { padding:12px; text-align:left; border-bottom:1px solid #475569; }
footer { text-align:center; color:#94a3b8; padding:25px; }
</style>
</head>
<body>
<header>
<h1>LAB - CIBERSEGURIDAD DEFENSIVA</h1>
<p>Laboratorio de análisis de logs y eventos de seguridad</p>
{% if usuario %}
<nav>
<a href="/dashboard">Inicio</a>
<a href="/usuarios">Usuarios</a>
<a href="/consultas">Consultas</a>
<a href="/documentos">Documentos</a>
<a href="/admin">Administración</a>
<a href="/logout">Salir</a>
</nav>
{% endif %}
</header>
<main>
<div class="panel">
<div class="brand-box">
<img src="{{ brand_avatar }}" alt="Huachimingo">
<div class="brand-meta">
<strong>{{ brand_name }}</strong>
<a href="{{ brand_link }}" target="_blank">@{{ brand_github }}</a>
</div>
</div>
<h2>{{ titulo }}</h2>
{% if mensaje %}<p>{{ mensaje }}</p>{% endif %}
{% if error %}<p class="error">{{ error }}</p>{% endif %}

{% if pagina == "login" %}
<form method="POST" action="/login">
<input name="usuario" placeholder="Usuario" required>
<input name="password" type="password" placeholder="Contraseña" required>
<button type="submit">Iniciar sesión</button>
</form>

{% elif pagina == "dashboard" %}
<p>Bienvenido, <b>{{ usuario }}</b>.</p>
<p>Seleccione un módulo del laboratorio.</p>
<div class="grid">
<a class="card" href="/usuarios">👥 Usuarios</a>
<a class="card" href="/consultas">🔍 Consultas</a>
<a class="card" href="/documentos">📁 Documentos</a>
<a class="card" href="/admin">⚙ Administración</a>
</div>

{% elif pagina == "usuarios" %}
<table>
<tr><th>ID</th><th>Usuario</th></tr>
{% for u in datos %}
<tr><td>{{ u["id"] }}</td><td>{{ u["usuario"] }}</td></tr>
{% endfor %}
</table>

{% elif pagina == "consultas" %}
<form method="GET" action="/consultas">
<input name="q" placeholder="Buscar usuario">
<button type="submit">Buscar</button>
</form>
{% if datos %}
<table>
<tr><th>ID</th><th>Resultado</th></tr>
{% for u in datos %}
<tr><td>{{ u["id"] }}</td><td>{{ u["usuario"] }}</td></tr>
{% endfor %}
</table>
{% endif %}

{% elif pagina == "documentos" %}
{% for d in datos %}
<p>
<a href="/documentos/{{ d['id'] }}">{{ d["nombre"] }}</a>
</p>
{% endfor %}

{% elif pagina == "detalle" %}
<p>{{ datos["descripcion"] }}</p>
<a href="/documentos">Volver a documentos</a>

{% elif pagina == "admin" %}
<p>Panel administrativo del laboratorio.</p>
<p>Acceso permitido únicamente al usuario operador.</p>
{% endif %}
</div>
</main>
<footer>Laboratorio académico | Docker - Nginx - Flask - Syslog</footer>
</body>
</html>
"""

def vista(titulo, pagina, datos=None, mensaje=None, error=None, codigo=200):
    return render_template_string(
        HTML,
        titulo=titulo,
        pagina=pagina,
        datos=datos,
        mensaje=mensaje,
        error=error,
        usuario=session.get("usuario"),
        brand_name=BRAND_NAME,
        brand_github=BRAND_GITHUB,
        brand_link=BRAND_LINK,
        brand_avatar=BRAND_AVATAR
    ), codigo

def auditar(evento, **campos):
    detalle = " ".join(f"{k}={v}" for k,v in campos.items())
    app.logger.info(
        "%s source_ip=%s user=%s %s",
        evento,
        request.remote_addr,
        session.get("usuario", "anonimo"),
        detalle
    )

def protegido():
    if not session.get("usuario"):
        auditar("ACCESS_DENIED", path=request.path)
        abort(401)

@app.route("/")
def inicio():
    if session.get("usuario"):
        return redirect("/dashboard")
    return vista("Inicio de sesión", "login")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return redirect("/")

    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")

    # VULNERABILIDAD INTENCIONAL DEL LABORATORIO
    sql = (
        "SELECT usuario FROM usuarios WHERE usuario='"
        + usuario + "' AND password='" + password + "'"
    )

    try:
        with conexion() as db:
            resultado = db.execute(sql).fetchone()

        if resultado:
            session.clear()
            session["usuario"] = resultado["usuario"]
            auditar("AUTH_SUCCESS")
            return redirect("/dashboard")

        auditar("AUTH_FAILED")
        return vista("Inicio de sesión", "login",
                     error="Credenciales incorrectas", codigo=401)

    except sqlite3.Error as e:
        auditar("SQL_ERROR", tipo=type(e).__name__)
        return vista("Error SQL", "login",
                     error="Error de consulta", codigo=400)

@app.route("/dashboard")
def dashboard():
    protegido()
    auditar("DASHBOARD_ACCESS")
    return vista("Panel principal", "dashboard")

@app.route("/usuarios")
def usuarios():
    protegido()
    auditar("USER_LIST_ACCESS")
    with conexion() as db:
        datos = db.execute(
            "SELECT id, usuario FROM usuarios"
        ).fetchall()
    return vista("Listado de usuarios", "usuarios", datos=datos)

@app.route("/consultas")
def consultas():
    protegido()
    q = request.args.get("q", "")
    auditar("SEARCH_REQUEST", longitud=len(q))
    with conexion() as db:
        datos = db.execute(
            "SELECT id, usuario FROM usuarios WHERE usuario LIKE ?",
            ("%" + q + "%",)
        ).fetchall()
    return vista("Consultas de usuarios", "consultas", datos=datos)

@app.route("/documentos")
def documentos():
    protegido()
    auditar("DOCUMENT_LIST_ACCESS")
    with conexion() as db:
        datos = db.execute(
            "SELECT id,nombre FROM documentos"
        ).fetchall()
    return vista("Documentos internos", "documentos", datos=datos)

@app.route("/documentos/<int:doc_id>")
def detalle(doc_id):
    protegido()
    with conexion() as db:
        dato = db.execute(
            "SELECT * FROM documentos WHERE id=?", (doc_id,)
        ).fetchone()

    if not dato:
        auditar("DOCUMENT_NOT_FOUND", document_id=doc_id)
        abort(404)

    auditar("DOCUMENT_ACCESS", document_id=doc_id)
    return vista(dato["nombre"], "detalle", datos=dato)

@app.route("/admin")
def admin():
    protegido()
    if session.get("usuario") != "operador":
        auditar("ACCESS_DENIED", path="/admin")
        abort(403)
    auditar("ADMIN_ACCESS")
    return vista("Administración", "admin")

@app.route("/logout")
def logout():
    auditar("LOGOUT_SUCCESS")
    session.clear()
    return redirect("/")

@app.errorhandler(401)
def error401(e):
    return vista("No autenticado", "error",
                 mensaje="Debe iniciar sesión.", codigo=401)

@app.errorhandler(403)
def error403(e):
    return vista("Acceso denegado", "error",
                 mensaje="No tiene permisos.", codigo=403)

@app.errorhandler(404)
def error404(e):
    auditar("PAGE_NOT_FOUND", path=request.path)
    return vista("Página no encontrada", "error",
                 mensaje="Recurso inexistente.", codigo=404)
