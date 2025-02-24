from flask import Flask, render_template, request, redirect, url_for
from jira_client import get_jira_client, MockJiraClient
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Sprint Manager Application")
parser.add_argument('--mock', action='store_true', help="Run with mock JIRA API")
args = parser.parse_args()

app = Flask(__name__)
jira = get_jira_client(use_mock=args.mock)
DATA_FILE = "data/teams.json"


def load_teams():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_teams(teams):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(teams, f, indent=2)


@app.route('/', methods=['GET', 'POST'])
def teams():
    teams = load_teams()
    boards = []
    team_board_names = {}
    start_at = int(request.args.get('start_at', 0))

    for team, board_id in teams.items():
        if board_id:
            if isinstance(jira, MockJiraClient):
                board = next((b for b in jira.boards if b["id"] == board_id), None)
                team_board_names[team] = board["name"] if board else "Unknown Board"
            else:
                try:
                    board_data = jira.search_boards(start_at=0, max_results=50)
                    board = next((b for b in board_data["values"] if b["id"] == board_id), None)
                    team_board_names[team] = board["name"] if board else "Unknown Board"
                except:
                    team_board_names[team] = "Error Fetching Board"

    if request.method == 'POST':
        if 'add_team' in request.form:
            team_name = request.form['team_name']
            if team_name and team_name not in teams:
                teams[team_name] = None
                save_teams(teams)
        elif 'search_board' in request.form:
            search_term = request.form['search_term']
            boards_data = jira.search_boards(search_term, start_at=start_at)
            boards = boards_data["values"]
            total_boards = boards_data["total"]
        elif 'map_board' in request.form:
            team_name = request.form['team_name']
            board_id = request.form['board_id']
            teams[team_name] = int(board_id)
            save_teams(teams)
        elif 'delete_team' in request.form:
            team_name = request.form['team_name']
            if team_name in teams:
                del teams[team_name]
                save_teams(teams)

    return render_template('teams.html', teams=teams, boards=boards, team_board_names=team_board_names,
                           start_at=start_at, total_boards=locals().get('total_boards', 0))


@app.route('/sprints/<team_name>')
def sprints(team_name):
    teams = load_teams()
    board_id = teams.get(team_name)
    if not board_id:
        return redirect(url_for('teams'))

    start_at = int(request.args.get('start_at', 0))
    sprints_data = jira.get_sprints(board_id, start_at=start_at)
    return render_template('sprints.html', team_name=team_name, sprints=sprints_data["values"],
                           start_at=start_at, total_sprints=sprints_data["total"])


@app.route('/properties/<team_name>/<int:sprint_id>', methods=['GET', 'POST'])
def properties(team_name, sprint_id):
    default_props = {"Planned": 0, "Capacity": 0}
    custom_props = {}

    if request.method == 'POST':
        for key in default_props:
            value = request.form.get(key)
            if value is not None:
                try:
                    int_value = int(value)
                    if key == "Capacity" and not (0 <= int_value <= 100):
                        continue
                    jira.set_sprint_property(sprint_id, key, int_value)
                except ValueError:
                    continue

        new_key = request.form.get('new_key')
        new_value = request.form.get('new_value')
        if new_key and new_value:
            jira.set_sprint_property(sprint_id, new_key, new_value)

    for key in default_props:
        value = jira.get_sprint_property(sprint_id, key)
        if value is not None:
            default_props[key] = value

    if isinstance(jira, MockJiraClient):
        all_props = jira.properties.get(sprint_id, {})
        custom_props = {k: v for k, v in all_props.items() if k not in default_props}

    return render_template('properties.html',
                           team_name=team_name,
                           sprint_id=sprint_id,
                           default_props=default_props,
                           custom_props=custom_props)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)