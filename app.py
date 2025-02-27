from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, disconnect, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, manage_session=False)

# Estructura para almacenar las salas:
# rooms = {
#    room_id: {
#         "players": { sid: { "alias": str, "ready": bool, "repartir": bool } },
#         "game_data": { "words": list, "impostor": sid }
#    }
# }
rooms = {}

# Lista de 100 palabras en español
words_pool = [
    # Primeras 50
    "gato", "perro", "casa", "árbol", "cielo", "agua", "fuego", "tierra", "aire", "libro",
    "sol", "luna", "estrella", "coche", "montaña", "río", "mar", "flor", "jardín", "ciudad",
    "zapato", "mesa", "silla", "ventana", "puerta", "reloj", "computadora", "teléfono", "camisa", "pantalón",
    "sombrero", "camión", "tren", "avión", "barco", "bicicleta", "parque", "escuela", "universidad", "hospital",
    "mercado", "restaurante", "café", "pan", "queso", "vino", "cerveza", "música", "película", "teatro",
    # Siguientes 50
    "juego", "dinero", "pueblo", "edificio", "calle", "puente", "plaza", "ciudadela", "museo", "iglesia",
    "biblioteca", "mercancía", "sabor", "aroma", "color", "forma", "línea", "cubo", "esfera", "triángulo",
    "cuadrado", "rectángulo", "pintura", "escultura", "poesía", "novela", "cuento", "ensayo", "misterio", "aventura",
    "drama", "comedia", "acción", "romance", "suspenso", "horror", "fantasía", "ciencia", "tecnología", "naturaleza",
    "energía", "fuerza", "velocidad", "tiempo", "espacio", "universo", "realidad", "sueño", "imaginación", "creatividad"
]

def generate_room_id(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Página de inicio: Permite ingresar alias y código de sala.
    Si se deja vacío el código, se genera uno nuevo.
    """
    if request.method == "POST":
        alias = request.form.get("alias")
        room = request.form.get("room")
        if not alias:
            return redirect(url_for("index"))
        if not room:
            room = generate_room_id()
        session["alias"] = alias
        session["room"] = room
        # Crear la sala si no existe
        if room not in rooms:
            rooms[room] = {"players": {}, "game_data": {}}
        return redirect(url_for("room", room_id=room))
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Ingreso a la Sala</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://fonts.googleapis.com/css2?family=Fredoka+One&display=swap" rel="stylesheet">
      <style>
         body {
             background: linear-gradient(135deg, #89f7fe, #66a6ff);
             font-family: 'Fredoka One', cursive;
             color: #333;
         }
         .card {
             border-radius: 15px;
             box-shadow: 0 4px 6px rgba(0,0,0,0.1);
         }
         .form-control, .btn {
             border-radius: 25px;
         }
         .container {
             max-width: 400px;
             margin-top: 10vh;
         }
      </style>
    </head>
    <body>
       <div class="container">
         <div class="card p-4">
           <h1 class="text-center mb-4">¡Bienvenido!</h1>
           <form method="post">
             <div class="mb-3">
               <input type="text" class="form-control" name="alias" placeholder="Tu alias" required>
             </div>
             <div class="mb-3">
               <input type="text" class="form-control" name="room" placeholder="Código de sala (dejar vacío para nueva)">
             </div>
             <button type="submit" class="btn btn-primary w-100">Entrar</button>
           </form>
         </div>
       </div>
    </body>
    </html>
    ''')

@app.route("/room/<room_id>")
def room(room_id):
    """
    Página del lobby para la sala especificada.
    Se muestra la lista de jugadores y el botón "Empezar".
    En el juego se ve la lista de palabras (numeradas) y se incluye el código de sala debajo de los usuarios.
    (Se ha eliminado el encabezado superior de la sala).
    """
    if "alias" not in session or "room" not in session or session["room"] != room_id:
        return redirect(url_for("index"))
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Sala de Juego</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://fonts.googleapis.com/css2?family=Fredoka+One&display=swap" rel="stylesheet">
      <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
      <style>
          body {
              background: #e0f7fa;
              font-family: 'Fredoka One', cursive;
          }
          .container-fluid {
              padding: 20px;
          }
          .card {
              border-radius: 15px;
              box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          }
          .btn {
              border-radius: 25px;
          }
          #lobby, #game {
              margin-top: 20px;
          }
          #players_list li, #game_players_list li {
              list-style: none;
              padding: 5px 0;
          }
          #sidebar {
              max-width: 200px;
          }
          @media (max-width: 576px) {
              #container {
                  flex-direction: column;
              }
              #sidebar {
                  margin-top: 20px;
              }
          }
          .room-code {
              margin-top: 15px;
              font-size: 0.9em;
              color: #555;
          }
      </style>
    </head>
    <body>
      <div class="container-fluid">
          <div class="text-center mb-3">
              <h2>Bienvenido, {{ session['alias'] }}</h2>
              Sala: <strong>{{ room_id }}</strong>
          </div>
          <!-- Sección de lobby -->
          <div id="lobby" class="card p-4 mx-auto" style="max-width:600px;">
              <h3 class="mb-3">Lobby</h3>
              <div>
                  <h5>Jugadores en la sala:</h5>
                  <ul id="players_list" class="mb-3"></ul>
              </div>
              <div class="text-center">
                  <button id="ready_btn" class="btn btn-success">Empezar</button>
              </div>
          </div>
          <!-- Sección de juego (inicialmente oculta) -->
          <div id="game" class="card p-4 mx-auto" style="max-width:600px; display:none;">
              <h3 class="mb-3">Juego</h3>
              <div id="container" class="d-flex justify-content-between">
                  <div id="main" class="flex-fill">
                      <h5>Palabras:</h5>
                      <ul id="words_list"></ul>
                  </div>
                  <div id="sidebar" class="ms-3">
                      <h5>Jugadores:</h5>
                      <ul id="game_players_list"></ul>
                      <!-- Se muestra el código de sala para compartir -->
                      <div class="room-code text-center">
                          Sala: <strong>{{ room_id }}</strong>
                      </div>
                  </div>
              </div>
              <div class="mt-4 text-center">
                  <button id="repartir_btn" class="btn btn-primary me-2">Repartir</button>
                  <button id="salir_btn" class="btn btn-danger">Salir</button>
              </div>
          </div>
      </div>
      <script>
          var socket = io();
          
          // Actualiza la lista de jugadores en el lobby mostrando si están listos
          socket.on("update_players", function(data){
              var players_list = document.getElementById("players_list");
              players_list.innerHTML = "";
              data.players.forEach(function(player){
                  var li = document.createElement("li");
                  li.innerText = player.alias;
                  if (player.ready) {
                      li.innerHTML += " <span class='badge bg-success'>Listo</span>";
                  }
                  players_list.appendChild(li);
              });
          });
          
          // Cuando se inicie el juego, se actualiza la vista de juego
          socket.on("start_game", function(data){
              document.getElementById("lobby").style.display = "none";
              document.getElementById("game").style.display = "block";
              var words_list = document.getElementById("words_list");
              words_list.innerHTML = "";
              // Mostrar las palabras numeradas del 1 al 10
              data.words.forEach(function(word, index){
                  var li = document.createElement("li");
                  li.innerText = (index + 1) + ". " + word;
                  words_list.appendChild(li);
              });
              updateGamePlayers(data.players);
              console.log("Impostor es: " + data.impostor);
          });
          
          // Actualiza la lista de jugadores en la vista de juego mostrando el estado de repartir
          function updateGamePlayers(players) {
              var game_players_list = document.getElementById("game_players_list");
              game_players_list.innerHTML = "";
              players.forEach(function(player){
                  var li = document.createElement("li");
                  li.innerHTML = player.alias;
                  if (player.repartir) {
                      li.innerHTML += " <span class='badge bg-success'>Listo</span>";
                  }
                  game_players_list.appendChild(li);
              });
          }
          
          // Recibe actualizaciones del estado de repartir
          socket.on("update_repartir", function(data){
              updateGamePlayers(data.players);
          });
          
          // Al hacer clic en "Empezar", se deshabilita el botón y se envía el estado "ready" al servidor.
          document.getElementById("ready_btn").addEventListener("click", function(){
              this.disabled = true;
              socket.emit("player_ready");
          });
          
          // Botón "Repartir": simplemente emite el evento sin cambiar su apariencia.
          document.getElementById("repartir_btn").addEventListener("click", function(){
              socket.emit("toggle_repartir");
          });
          
          // Botón "Salir": desconecta y retorna a la pantalla inicial
          document.getElementById("salir_btn").addEventListener("click", function(){
              socket.emit("salir");
              window.location.href = "/";
          });
      </script>
    </body>
    </html>
    ''', room_id=room_id)

# Eventos de SocketIO

@socketio.on("connect")
def handle_connect():
    alias = session.get("alias")
    room_id = session.get("room")
    if not alias or not room_id:
        return False  # No se conecta si faltan datos
    join_room(room_id)
    if room_id not in rooms:
        rooms[room_id] = {"players": {}, "game_data": {}}
    # Inicializamos los estados: ready para empezar y repartir (toggle) para repartir
    rooms[room_id]["players"][request.sid] = {"alias": alias, "ready": False, "repartir": False}
    update_players_list(room_id)

@socketio.on("disconnect")
def handle_disconnect():
    room_id = session.get("room")
    if room_id and room_id in rooms and request.sid in rooms[room_id]["players"]:
        del rooms[room_id]["players"][request.sid]
        leave_room(room_id)
        update_players_list(room_id)
        update_repartir_status(room_id)

@socketio.on("player_ready")
def handle_player_ready():
    room_id = session.get("room")
    if not room_id or room_id not in rooms:
        return
    # Marcar al jugador como listo
    if request.sid in rooms[room_id]["players"]:
        rooms[room_id]["players"][request.sid]["ready"] = True
    # Si ya hay una partida en curso, se envía la info actual al jugador que acaba de pulsar "Empezar"
    if "words" in rooms[room_id]["game_data"] and rooms[room_id]["game_data"].get("words"):
        game_data = rooms[room_id]["game_data"]
        players_list = [{"alias": player["alias"], "repartir": player.get("repartir", False)} 
                        for player in rooms[room_id]["players"].values()]
        if request.sid == game_data["impostor"]:
            words = ["impostor"] * 10
        else:
            words = game_data["words"]
        emit("start_game", {
                "words": words,
                "players": players_list,
                "impostor": rooms[room_id]["players"][game_data["impostor"]]["alias"]
        }, room=request.sid)
        update_repartir_status(room_id)
    else:
        # Si no hay partida en curso, se espera a que todos estén listos para iniciar
        if rooms[room_id]["players"] and all(player["ready"] for player in rooms[room_id]["players"].values()):
            start_game(room_id)
        else:
            update_players_list(room_id)

@socketio.on("toggle_repartir")
def handle_toggle_repartir():
    room_id = session.get("room")
    if not room_id or room_id not in rooms:
        return
    if request.sid in rooms[room_id]["players"]:
        current = rooms[room_id]["players"][request.sid].get("repartir", False)
        rooms[room_id]["players"][request.sid]["repartir"] = not current
    update_repartir_status(room_id)
    if rooms[room_id]["players"] and all(player.get("repartir", False) for player in rooms[room_id]["players"].values()):
        start_game(room_id)

@socketio.on("salir")
def handle_salir():
    room_id = session.get("room")
    if room_id and room_id in rooms and request.sid in rooms[room_id]["players"]:
        del rooms[room_id]["players"][request.sid]
        leave_room(room_id)
        update_players_list(room_id)
        update_repartir_status(room_id)
    disconnect()

def update_players_list(room_id):
    if room_id in rooms:
        players_list = [{"alias": player["alias"], "ready": player.get("ready", False)} 
                        for player in rooms[room_id]["players"].values()]
        socketio.emit("update_players", {"players": players_list}, room=room_id)

def update_repartir_status(room_id):
    if room_id in rooms:
        players_status = [{"alias": player["alias"], "repartir": player.get("repartir", False)}
                           for player in rooms[room_id]["players"].values()]
        socketio.emit("update_repartir", {"players": players_status}, room=room_id)

def start_game(room_id):
    if room_id not in rooms or not rooms[room_id]["players"]:
        return
    random_words = random.sample(words_pool, 10)
    impostor_sid = random.choice(list(rooms[room_id]["players"].keys()))
    rooms[room_id]["game_data"] = {"words": random_words, "impostor": impostor_sid}
    players_list = []
    for player in rooms[room_id]["players"].values():
        player["ready"] = False
        player["repartir"] = False
        players_list.append({"alias": player["alias"], "repartir": False})
    for sid, player in rooms[room_id]["players"].items():
        if sid == impostor_sid:
            words = ["impostor"] * 10
        else:
            words = random_words
        socketio.emit("start_game", {
            "words": words,
            "players": players_list,
            "impostor": rooms[room_id]["players"][impostor_sid]["alias"]
        }, room=sid)
    update_repartir_status(room_id)

if __name__ == "__main__":
    socketio.run(app, debug=True)
