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

# Pick one random clue per category/value
for c, cat in enumerate(board):
    for val in VALUES:
        pool = [cl for cl in cat["clues"] if cl["value"] == val]
        if pool:
            selected_clues[(c, val)] = random.choice(pool)

HOST_HTML = """
<!doctype html>
<html>
<head>
<title>Gielinor Gauntlet</title>
<style>
body {
    background:#15120d;
    color:#e2d3a5;
    font-family:Arial;
    text-align:center;
}
table {
    margin:auto;
    border-collapse:collapse;
}
th, td {
    border:2px solid #9b8350;
    padding:18px;
    min-width:120px;
    background:#d7c9a1;
    color:black;
}
a {
    text-decoration:none;
    font-weight:bold;
    color:black;
}
input, button, select {
    padding:8px;
    margin:5px;
}
.scorebox {
    margin:10px;
    padding:10px;
    border:1px solid #9b8350;
    display:inline-block;
}
</style>
</head>

<body>

<h1>Gielinor Gauntlet</h1>

<form action="/add_player" method="post">
    <input name="name" placeholder="Player name">
    <button>Add Player</button>
</form>

<h2>Players</h2>

{% for p in players %}
<div class="scorebox">
    <b>{{p}}</b><br>
    {{scores[p]}} gp
</div>
{% endfor %}

<br><br>

<table>
<tr>
{% for cat in board %}
    <th>{{cat.category}}</th>
{% endfor %}
</tr>

{% for val in values %}
<tr>
{% for cat in board %}
    {% set key = loop.index0|string + "-" + val|string %}
    <td>
    {% if key in used %}
        ---
    {% else %}
        <a href="/clue/{{loop.index0}}/{{val}}">
            {{val}} gp
        </a>
    {% endif %}
    </td>
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
<style>
body{
    background:#15120d;
    color:#e2d3a5;
    font-family:Arial;
    text-align:center;
}
input, button, select{
    padding:10px;
    margin:8px;
}
</style>
</head>

<body>

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

<br>

<a href="/">Back</a>

</body>
</html>
"""

RESULT_HTML = """
<!doctype html>
<html>
<head>
<title>Result</title>
<style>
body{
    background:#15120d;
    color:#e2d3a5;
    font-family:Arial;
    text-align:center;
}
a{
    color:#e2d3a5;
}
</style>
</head>

<body>

<h1>{{result}}</h1>

<h2>Correct answer:</h2>

<h1>{{correct}}</h1>

<br>

<a href="/">Return to Board</a>

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
