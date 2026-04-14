from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from textwrap import dedent


class ManualRunQueue:
    def __init__(self, process_run: Callable[[int], None]) -> None:
        self._process_run = process_run
        self.pending_run_ids: list[int] = []

    def enqueue(self, run_id: int) -> None:
        self.pending_run_ids.append(run_id)

    def run_next(self) -> int | None:
        if not self.pending_run_ids:
            return None

        run_id = self.pending_run_ids.pop(0)
        self._process_run(run_id)
        return run_id

    def run_all(self) -> list[int]:
        processed: list[int] = []

        while self.pending_run_ids:
            run_id = self.run_next()
            if run_id is not None:
                processed.append(run_id)

        return processed

    def shutdown(self) -> None:
        return None


def create_fake_solo_wargame_repo(repo_root: Path) -> Path:
    package_root = repo_root / "solo_wargame_ai"
    cli_root = package_root / "cli"
    missions_root = repo_root / "configs" / "missions"

    cli_root.mkdir(parents=True, exist_ok=True)
    missions_root.mkdir(parents=True, exist_ok=True)

    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (cli_root / "__init__.py").write_text("", encoding="utf-8")

    for mission_name in (
        "mission_01_secure_the_woods_1.toml",
        "mission_03_secure_the_building.toml",
        "malformed_output.toml",
    ):
        (missions_root / mission_name).write_text(f"# {mission_name}\n", encoding="utf-8")

    (cli_root / "episode_batch_runner.py").write_text(
        dedent(
            """
            from __future__ import annotations

            import argparse
            import json
            import sys
            from pathlib import Path


            def _resolved_seeds(seed_spec: dict[str, object]) -> list[int]:
                if seed_spec["kind"] == "range":
                    return list(range(seed_spec["start"], seed_spec["stop"]))
                return list(seed_spec["seeds"])


            def _write_json(path: Path, payload: object) -> None:
                path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


            def main() -> int:
                parser = argparse.ArgumentParser()
                parser.add_argument("--request-file", required=True)
                args = parser.parse_args()

                request_path = Path(args.request_file)
                payload = json.loads(request_path.read_text(encoding="utf-8"))
                artifact_dir = Path(payload["artifact_dir"])
                artifact_dir.mkdir(parents=True, exist_ok=True)

                mission_path = Path.cwd() / payload["mission_path"]
                if mission_path.name == "malformed_output.toml":
                    print("{not valid json")
                    return 0

                seeds = _resolved_seeds(payload["seed_spec"])
                execution = {
                    "mission_id": mission_path.stem,
                    "mission_path": str(mission_path.resolve()),
                    "policy": {
                        "kind": payload["policy"]["kind"],
                        "name": payload["policy"]["name"],
                        "resolved_agent_name": "HeuristicAgent",
                    },
                    "seed_spec": payload["seed_spec"],
                    "resolved_seed_count": len(seeds),
                    "git_commit": "abcdef0",
                    "git_dirty": False,
                    "python_version": "3.11.0",
                    "duration_sec": 0.123456,
                }

                if payload["policy"]["name"] == "exact_guided_heuristic":
                    result = {
                        "schema_version": "solo_wargame_runner_v1",
                        "status": "failed",
                        "operation": "episode_batch",
                        "execution": execution,
                        "artifacts": [
                            {
                                "kind": "request",
                                "path": str((artifact_dir / "request.json").resolve()),
                                "format": "json",
                                "description": "normalized episode-batch request payload",
                            },
                            {
                                "kind": "result",
                                "path": str((artifact_dir / "result.json").resolve()),
                                "format": "json",
                                "description": "machine-readable episode-batch result payload",
                            },
                        ],
                        "warnings": [],
                        "error": {
                            "kind": "policy_resolution_error",
                            "message": "builtin policy 'exact_guided_heuristic' does not support this mission",
                        },
                    }
                    _write_json(artifact_dir / "request.json", payload)
                    _write_json(artifact_dir / "result.json", result)
                    print(json.dumps(result, indent=2, sort_keys=True))
                    return 1

                artifacts = [
                    {
                        "kind": "request",
                        "path": str((artifact_dir / "request.json").resolve()),
                        "format": "json",
                        "description": "normalized episode-batch request payload",
                    },
                    {
                        "kind": "result",
                        "path": str((artifact_dir / "result.json").resolve()),
                        "format": "json",
                        "description": "machine-readable episode-batch result payload",
                    },
                ]

                if payload.get("write_episode_rows"):
                    episode_rows_path = artifact_dir / "episodes.jsonl"
                    rows = [
                        json.dumps({"seed": seed, "outcome": "victory"})
                        for seed in seeds
                    ]
                    episode_rows_path.write_text("\\n".join(rows) + "\\n", encoding="utf-8")
                    artifacts.insert(
                        1,
                        {
                            "kind": "episode_rows",
                            "path": str(episode_rows_path.resolve()),
                            "format": "jsonl",
                            "description": "one row per completed episode",
                            "episode_count": len(seeds),
                        },
                    )

                result = {
                    "schema_version": "solo_wargame_runner_v1",
                    "status": "succeeded",
                    "operation": "episode_batch",
                    "metrics": {
                        "agent_name": "HeuristicAgent",
                        "episode_count": len(seeds),
                        "victory_count": len(seeds),
                        "defeat_count": 0,
                        "win_rate": 1.0,
                        "defeat_rate": 0.0,
                        "mean_terminal_turn": 5.0,
                        "mean_resolved_marker_count": 4.0,
                        "mean_removed_german_count": 1.0,
                        "mean_player_decision_count": 9.0,
                    },
                    "execution": execution,
                    "artifacts": artifacts,
                    "warnings": [],
                }

                _write_json(artifact_dir / "request.json", payload)
                _write_json(artifact_dir / "result.json", result)
                print(json.dumps(result, indent=2, sort_keys=True))
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root
