from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

class Player:
    def __init__(self, name):
        self.name = name
        self.health: int = 10
        self.choice: int = None

    def __eq__(self, other):
        if isinstance(other, Player):
            return self.name == other.name
        return self.name == other


# rooms maps room code -> {
#   "members": dict[Player]  - players currently in the room
#   "messages": list[dict]   - {"name": str, "message": str} log of chat/number-submission events
# }
rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        joinRandom = request.form.get("random", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        if create != False:
            code = generate_unique_code(4);
            rooms[code] = {"members": {}, "messages": []}
        elif join != False:
            if not code:
                return render_template("home.html", error="Please enter a room code.", code=code, name=name)
            elif code not in rooms:
                return render_template("home.html", error="Room does not exist.", code=code, name=name)
            elif len(rooms[code]["members"]) > 5:
                return render_template("home.html", error="Room is full.", code=code, name=name)
        elif joinRandom != False:
            code = filter(lambda r: len(r["members"]) < 5, rooms).next()
        session["room"] = code
        session["name"] = name
        rooms[code]["members"][name] = (Player(name))
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    choice = session.get("choice")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    # TODO: refactor?
    room_data = rooms[room]
    return render_template("room.html", code=room, messages=room_data["messages"], members=room_data["members"])

@socketio.on("message")
def message(data):
    name = session.get("name")
    room = session.get("room")
    if room not in rooms:
        return 
    choice = data["data"]
    rooms[room]["members"][name].choice = choice
    content = {
        "name": name,
        "message": choice
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"][name] = (Player(name))
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        members = rooms[room]["members"]
        members.remove(name)
        if len(members) <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, port=8000, debug=True)