"""SQLite persistence (stdlib only). All access is serialized with one lock."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS learners(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, seed INTEGER NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS queue(
  id INTEGER PRIMARY KEY, learner_id INTEGER NOT NULL, batch INTEGER NOT NULL,
  token TEXT NOT NULL, phase TEXT NOT NULL,
  target TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_queue ON queue(learner_id, done, id);
CREATE TABLE IF NOT EXISTS attempts(
  id INTEGER PRIMARY KEY, learner_id INTEGER NOT NULL, queue_id INTEGER NOT NULL,
  token TEXT NOT NULL, phase TEXT NOT NULL, target TEXT NOT NULL,
  answer TEXT NOT NULL, outcome TEXT NOT NULL, ts TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_attempts ON attempts(learner_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = "tutor.db"):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(SCHEMA)

    def _one(self, sql, args=()):
        with self._lock:
            return self._db.execute(sql, args).fetchone()

    def _all(self, sql, args=()):
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def _write(self, sql, args=()):
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur.lastrowid

    def create_learner(self, name: str, seed: int) -> int:
        return self._write("INSERT INTO learners(name, seed, created) VALUES(?,?,?)", (name, seed, _now()))

    def learner(self, learner_id: int):
        return self._one("SELECT * FROM learners WHERE id=?", (learner_id,))

    def add_queue(self, learner_id: int, phase: str, items: list[tuple[str, str]]) -> None:
        with self._lock:
            batch = self._db.execute("SELECT COALESCE(MAX(batch),0)+1 FROM queue WHERE learner_id=?",
                                     (learner_id,)).fetchone()[0]
            self._db.executemany(
                "INSERT INTO queue(learner_id,batch,token,phase,target) VALUES(?,?,?,?,?)",
                [(learner_id, batch, tok, phase, tgt) for tok, tgt in items])
            self._db.commit()

    def first_undone(self, learner_id: int):
        return self._one("SELECT * FROM queue WHERE learner_id=? AND done=0 ORDER BY id LIMIT 1", (learner_id,))

    def queue_item(self, queue_id: int):
        return self._one("SELECT * FROM queue WHERE id=?", (queue_id,))

    def batch_progress(self, learner_id: int, batch: int) -> tuple[int, int]:
        r = self._one("SELECT COUNT(*) AS n, SUM(done) AS d FROM queue WHERE learner_id=? AND batch=?",
                      (learner_id, batch))
        return int(r["d"] or 0), int(r["n"])

    def record_attempt(self, learner_id, queue_row, answer: str, outcome: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO attempts(learner_id,queue_id,token,phase,target,answer,outcome,ts) VALUES(?,?,?,?,?,?,?,?)",
                (learner_id, queue_row["id"], queue_row["token"], queue_row["phase"],
                 queue_row["target"], answer, outcome, _now()))
            self._db.execute("UPDATE queue SET done=1 WHERE id=?", (queue_row["id"],))
            self._db.commit()

    def events(self, learner_id: int) -> list[tuple[str, str]]:
        rows = self._all("SELECT target, outcome FROM attempts WHERE learner_id=? ORDER BY id", (learner_id,))
        return [(r["target"], r["outcome"]) for r in rows]

    def attempts(self, learner_id: int) -> list[sqlite3.Row]:
        return self._all("SELECT * FROM attempts WHERE learner_id=? ORDER BY id", (learner_id,))

    def clear_undone(self, learner_id: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM queue WHERE learner_id=? AND done=0", (learner_id,))
            self._db.commit()

    def list_learners(self) -> list[sqlite3.Row]:
        return self._all(
            "SELECT l.*, (SELECT COUNT(*) FROM attempts a WHERE a.learner_id=l.id) AS answered "
            "FROM learners l ORDER BY l.id DESC"
        )

    def reset_learner(self, learner_id: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM attempts WHERE learner_id=?", (learner_id,))
            self._db.execute("DELETE FROM queue WHERE learner_id=?", (learner_id,))
            self._db.commit()



