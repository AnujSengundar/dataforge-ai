"""Normalize the 2016 final from an official Cricsheet JSON archive."""

import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile


def main() -> None:
    with ZipFile(sys.argv[1]) as archive:
        raw = archive.read("951373.json")
    match = json.loads(raw)
    first, chase = match["innings"]
    assert chase["team"] == "West Indies" and match["info"]["overs"] == 20
    deliveries = [
        [
            over["over"] + 1,
            ball["batter"],
            ball["bowler"],
            ball["runs"]["total"],
            not bool({"wides", "noballs"} & ball.get("extras", {}).keys()),
            len([w for w in ball.get("wickets", []) if w["kind"] != "retired hurt"]),
        ]
        for over in chase["overs"]
        for ball in over["deliveries"]
    ]
    target = 1 + sum(
        ball["runs"]["total"] for over in first["overs"] for ball in over["deliveries"]
    )
    assert target == 156 and sum(row[3] for row in deliveries) == 161
    payload = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_revision": match["meta"]["revision"],
        "target": target,
        "deliveries": deliveries,
    }
    Path(__file__).with_name("cricket.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
