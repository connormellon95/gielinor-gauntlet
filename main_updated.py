from flask import Flask, render_template_string, request, redirect, url_for
import json
import random

app = Flask(__name__)

with open("questions.json", "r", encoding="utf-8") as f:
    board = json.load(f)

players = []
scores = {}
used_tiles = set()
selected_clues = {}

VALUES = [100, 200, 300, 400, 500]

for c, cat in enumerate(board):
    for val in VALUES:
        pool = [cl for cl in cat["clues"] if cl["value"] == val]
        if pool:
            selected_clues[(c, val)] = random.choice(pool)

STYLE = """
<style>
body {
    margin: 0;
    background: #15120d;
    color: #e2d3a5;
    font-family: Georgia, serif;
    text-align: center;
}

h1 {
    color: #d6b84f;
    font-size: 42px;
    margin-top: 20px;
    margin-bottom: 8px;
    text-shadow: 2px 2px #000;
}

h2 {
    color: #e2d3a5;
}

.topbar {
    padding: 18px;
}

button, input, select {
    font-family: Georgia, serif;
    font-weight: bold;
    padding: 10px;
    margin: 6px;
    border: 2px solid #6f5f3b;
    background: #d7c9a1;
    color: #1a140b;
}

button:hover, a.tile:hover {
    background: #c9a227;
    cursor: pointer;
}

.players {
    margin: 15px auto 25px auto;
    padding: 12px;
    border: 3px solid #6f5f3b;
    background: #252117;
    width: 85%;
    min-height: 70px;
}

.scorebox {
    display: inline-block;
    min-width: 140px;
    margin: 8px;
    padding: 12px;
    border: 3px ridge #6f5f3b;
    background: #d7c9a1;
    color: #1a140b;
    font-size: 18px;
}

.score {
    font-size: 24px;
    color: #2f8f46;
    font-weight: bold;
}

.board {
    width: 85%;
    margin: auto;
    border-collapse: separate;
    border-spacing: 8px;
}

.board th {
    background: #cdbb8d;
    color: #1a140b;
    border: 3px ridge #6f5f3b;
    padding: 16px;
    font-size: 22px;
}

.board td {
    background: #d7c9a1;
    border: 3px ridge #6f5f3b;
    height: 65px;
    min-width: 120px;
    color: #1a140b;
    font-size: 20px;
    font-weight: bold;
}

a.tile {
    display: block;
    padding: 20px;
    color: #1a140b;
    text-decoration: none;
}

.used {
    background: #8d8d8d !important;
    color: #555 !important;
}

.card {
    width: 70%;
    margin: 80px auto;
    background: #d7c9a1;
    color: #1a140b;
    border: 5px ridge #6f5f3b;
    padding: 30px;
}

.card h1 {
    color: #1a140b;
    text-shadow: none;
}

.backlink {
    color: #e2d3a5;
    font-weight: bold;
}

.music-btn {
    position: fixed;
    top: 15px;
    right: 15px;
}
</style>
"""

MUSIC_SCRIPT = """
<audio id="bgMusic" loop>
    <source src="https://files.catbox.moe/2m6j0n.mp3" type="audio/mpeg">
</audio>

<button class="music-btn" onclick="toggleMusic()">Music On/Off</button>

<script>
let music = document.getElementById("bgMusic");

function toggleMusic() {
    if (music.paused) {
        music.volume = 0.35;
        music.play();
    } else {
        music.pause();
    }
}
</script>
"""

HOST_HTML = """
<!doctype html>
<html>
<head>
<title>Gielinor Gauntlet</title>
""" + STYLE + """
<meta http-equiv="refresh" content="8">
</head>

<body>
""" + MUSIC_SCRIPT + """

<div class="topbar">
    <h1>Gielinor Gauntlet</h1>

    <form action="/add_player" method="post">
        <input name="name" placeholder="Player name">
        <button>Add Player</button>
    </form>
</div>

<div class="players">
    <h2>Adventurers</h2>

    {% for p in players %}
    <div class="scorebox">
        <b>{{p}}</b><br>
        <span class="score">{{scores[p]}} gp</span>
    </div>
    {% endfor %}
</div>

<table class="board">
<tr>
{% for cat in board %}
    <th>{{cat.category}}</th>
{% endfor %}
</tr>

{% for val in values %}
<tr>
{% for cat in board %}
    {% set key = loop.index0|string + "-" + val|string %}
    {% if key in used %}
        <td class="used">—</td>
    {% else %}
        <td>
            <a class="tile" href="/clue/{{loop.index0}}/{{val}}">
                {{val}} gp
            </a>
        </td>
    {% endif %}
{% endfor %}
</tr>
{% endfor %}
</table>

</body>
</html>
"""

CLUE_HTML = """
<!doctype html>
<html>
<head>
<title>Question</title>
""" + STYLE + """
</head>

<body>
""" + MUSIC_SCRIPT + """

<div class="card">
    <h1>{{clue.question}}</h1>
    <h2>{{value}} gp</h2>

    <form action="/answer" method="post">
        <input type="hidden" name="cat_idx" value="{{cat_idx}}">
        <input type="hidden" name="value" value="{{value}}">

        <select name="player">
        {% for p in players %}
            <option value="{{p}}">{{p}}</option>
        {% endfor %}
        </select>

        <br>

        <input name="answer" placeholder="Answer here">

        <br>

        <button>Submit Answer</button>
    </form>
</div>

<a class="backlink" href="/">Back to Board</a>

</body>
</html>
"""

RESULT_HTML = """
<!doctype html>
<html>
<head>
<title>Result</title>
""" + STYLE + """
<meta http-equiv="refresh" content="4;url=/">
</head>

<body>
""" + MUSIC_SCRIPT + """

<div class="card">
    <h1>{{result}}</h1>

    <h2>Correct answer:</h2>
    <h1>{{correct}}</h1>

    <p>Returning to board...</p>
</div>

<a class="backlink" href="/">Return to Board</a>

</body>
</html>
"""

@app.route("/")
def host():
    used = {f"{c}-{v}" for c, v in used_tiles}
    return render_template_string(
        HOST_HTML,
        board=board,
        values=VALUES,
        players=players,
        scores=scores,
        used=used
    )

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name", "").strip()
    if name and name not in players:
        players.append(name)
        scores[name] = 0
    return redirect(url_for("host"))

@app.route("/clue/<int:cat_idx>/<int:value>")
def clue(cat_idx, value):
    clue_data = selected_clues.get((cat_idx, value))
    if not clue_data:
        return "Missing clue"

    return render_template_string(
        CLUE_HTML,
        clue=clue_data,
        value=value,
        cat_idx=cat_idx,
        players=players
    )

@app.route("/answer", methods=["POST"])
def answer():
    cat_idx = int(request.form["cat_idx"])
    value = int(request.form["value"])
    player = request.form["player"]

    user_answer = request.form["answer"].strip().lower()
    clue_data = selected_clues[(cat_idx, value)]
    correct_answer = str(clue_data["answer"]).strip().lower()

    if user_answer == correct_answer:
        scores[player] += value
        result = f"{player} got it RIGHT! +{value} gp"
    else:
        scores[player] -= value
        result = f"{player} got it WRONG! -{value} gp"

    used_tiles.add((cat_idx, value))

    return render_template_string(
        RESULT_HTML,
        result=result,
        correct=clue_data["answer"]
    )

if __name__ == "__main__":
    app.run()
