import json
from pathlib import Path


POLICY_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "policies.json"
)


def load_policies():
    """Load all policy records from the JSON file."""
    with open(POLICY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_verified_policies():
    """Return only policies with verified source information."""
    policies = load_policies()

    return [
        policy
        for policy in policies
        if policy.get("verified") is True
        and policy.get("text_en")
        and policy.get("source_url")
    ]
