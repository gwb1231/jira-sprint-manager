import requests
import json
from config import Config
import datetime

class JiraClient:
    def __init__(self):
        self.base_url = Config.JIRA_URL
        self.auth = (Config.JIRA_USERNAME, Config.JIRA_API_TOKEN)
        self.headers = {"Content-Type": "application/json"}

    def search_boards(self, name_filter="", start_at=0, max_results=50):
        url = f"{self.base_url}/rest/agile/1.0/board"
        params = {
            "name": name_filter if name_filter else None,
            "startAt": start_at,
            "maxResults": max_results
        }
        response = requests.get(url, auth=self.auth, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "values": data["values"],
            "startAt": data.get("startAt", start_at),
            "maxResults": data.get("maxResults", max_results),
            "total": data.get("total")
        }

    def get_sprints(self, board_id, start_at=0, max_results=50):
        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
        params = {
            "state": "active,future",
            "startAt": start_at,
            "maxResults": max_results
        }
        response = requests.get(url, auth=self.auth, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "values": data["values"],
            "startAt": data.get("startAt", start_at),
            "maxResults": data.get("maxResults", max_results),
            "total": data.get("total")
        }

    def get_sprint_property(self, sprint_id, property_key):
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/properties/{property_key}"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["value"]

    def set_sprint_property(self, sprint_id, property_key, value):
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/properties/{property_key}"
        data = json.dumps({"value": value})
        response = requests.put(url, auth=self.auth, headers=self.headers, data=data)
        response.raise_for_status()
        return True

class MockJiraClient:
    def __init__(self):
        self.boards = [
            {"id": i, "name": f"Team {chr(65+i-1)} Board"} for i in range(1, 101)  # 100 boards
        ]
        self.sprints = {
            board["id"]: [
                {"id": board["id"] * 100 + j, "name": f"Sprint {j}", "state": "active" if j % 2 == 0 else "future",
                 "startDate": "2025-02-20T00:00:00Z", "endDate": "2025-03-05T00:00:00Z"}
                for j in range(1, 61)  # 60 sprints per board
            ] for board in self.boards[:5]  # Only first 5 boards have sprints
        }
        self.properties = {sprint["id"]: {} for board_sprints in self.sprints.values() for sprint in board_sprints}

    def search_boards(self, name_filter="", start_at=0, max_results=50):
        filtered = [b for b in self.boards if not name_filter or name_filter.lower() in b["name"].lower()]
        total = len(filtered)
        start = min(start_at, total)
        end = min(start + max_results, total)
        return {
            "values": filtered[start:end],
            "startAt": start,
            "maxResults": min(max_results, total - start),
            "total": total
        }

    def get_sprints(self, board_id, start_at=0, max_results=50):
        sprints = self.sprints.get(board_id, [])
        total = len(sprints)
        start = min(start_at, total)
        end = min(start + max_results, total)
        return {
            "values": sprints[start:end],
            "startAt": start,
            "maxResults": min(max_results, total - start),
            "total": total
        }

    def get_sprint_property(self, sprint_id, property_key):
        return self.properties.get(sprint_id, {}).get(property_key)

    def set_sprint_property(self, sprint_id, property_key, value):
        if sprint_id not in self.properties:
            self.properties[sprint_id] = {}
        self.properties[sprint_id][property_key] = value
        return True

def get_jira_client(use_mock=False):
    return MockJiraClient() if use_mock else JiraClient()