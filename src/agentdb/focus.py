import sqlite3
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple


class FocusGraph:
    """Breadth-first traversal across symbol relationships stored in `edges`."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._symbol_cache: Dict[int, Dict[str, Any]] = {}

    def get_context(
        self,
        repo_path: str,
        symbol_name: str,
        depth: int,
        include_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return the primary symbol plus neighbors up to `depth` hops."""
        symbol = self._symbol_by_name(repo_path, symbol_name)
        if not symbol:
            return {
                "error": "symbol_not_found",
                "symbol": symbol_name,
                "repo_path": repo_path,
            }

        if depth <= 0:
            return {
                "primary": self._serialize_primary(symbol),
                "neighbors": {},
                "edges": [],
                "stats": {
                    "symbols_returned": 1,
                    "edges_traversed": 0,
                    "max_depth_reached": 0,
                },
            }

        type_set = {t for t in (include_types or []) if t}
        neighbors_by_depth: Dict[str, List[Dict[str, Any]]] = {}
        visited: Set[int] = {symbol["id"]}
        queue: deque[Tuple[int, int]] = deque([(symbol["id"], 0)])
        edges_seen: Set[Tuple[int, int, str]] = set()
        edges_payload: List[Dict[str, Any]] = []

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            edges = self._edges_incident(current_id, type_set)
            for edge in edges:
                edge_key = (edge["src_id"], edge["dst_id"], edge["edge_type"])
                if edge_key not in edges_seen:
                    serialized = self._serialize_edge(edge)
                    if serialized:
                        edges_payload.append(serialized)
                        edges_seen.add(edge_key)

                neighbor_id = (
                    edge["dst_id"] if current_id == edge["src_id"] else edge["src_id"]
                )
                if neighbor_id in visited:
                    continue
                neighbor = self._symbol_by_id(neighbor_id)
                if not neighbor or neighbor["repo_path"] != repo_path:
                    continue
                next_depth = current_depth + 1
                if next_depth > depth:
                    continue
                visited.add(neighbor_id)
                queue.append((neighbor_id, next_depth))
                bucket = neighbors_by_depth.setdefault(f"depth_{next_depth}", [])
                bucket.append(self._serialize_neighbor(neighbor))

        # Sort neighbors for deterministic output
        for bucket in neighbors_by_depth.values():
            bucket.sort(key=lambda item: (item.get("name") or "", item.get("kind") or ""))

        edges_payload.sort(
            key=lambda item: (
                item["source"]["name"],
                item["target"]["name"],
                item["type"],
            )
        )

        max_depth = 0
        if neighbors_by_depth:
            max_depth = max(int(key.split("_")[1]) for key in neighbors_by_depth)

        return {
            "primary": self._serialize_primary(symbol),
            "neighbors": neighbors_by_depth,
            "edges": edges_payload,
            "stats": {
                "symbols_returned": 1
                + sum(len(bucket) for bucket in neighbors_by_depth.values()),
                "edges_traversed": len(edges_payload),
                "max_depth_reached": max_depth,
            },
        }

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _symbol_by_name(self, repo_path: str, name: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT id, repo_path, name, kind, l0_overview, l1_contract, l2_pseudocode,
                   start_line, end_line
            FROM symbols
            WHERE repo_path = ? AND name = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (repo_path, name),
        ).fetchone()
        return dict(row) if row else None

    def _symbol_by_id(self, symbol_id: int) -> Optional[Dict[str, Any]]:
        cached = self._symbol_cache.get(symbol_id)
        if cached is not None:
            return cached
        row = self.conn.execute(
            """
            SELECT id, repo_path, name, kind, l0_overview, l1_contract, l2_pseudocode,
                   start_line, end_line
            FROM symbols
            WHERE id = ?
            """,
            (symbol_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        self._symbol_cache[symbol_id] = data
        return data

    def _edges_incident(
        self,
        symbol_id: int,
        include_types: Set[str],
    ) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT src_id, dst_id, edge_type FROM edges WHERE src_id = ? OR dst_id = ?",
            (symbol_id, symbol_id),
        ).fetchall()
        edges: List[Dict[str, Any]] = []
        for row in rows:
            edge_type = row["edge_type"]
            if include_types and edge_type not in include_types:
                continue
            edges.append(
                {
                    "src_id": row["src_id"],
                    "dst_id": row["dst_id"],
                    "edge_type": edge_type,
                }
            )
        return edges

    def _serialize_primary(self, symbol: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": symbol["id"],
            "repo_path": symbol["repo_path"],
            "name": symbol["name"],
            "kind": symbol["kind"],
            "l0_overview": symbol["l0_overview"],
            "l1_contract": symbol["l1_contract"],
            "start_line": symbol["start_line"],
            "end_line": symbol["end_line"],
        }

    def _serialize_neighbor(self, symbol: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": symbol["id"],
            "repo_path": symbol["repo_path"],
            "name": symbol["name"],
            "kind": symbol["kind"],
            "l0_overview": symbol["l0_overview"],
        }

    def _serialize_edge(self, edge: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        src = self._symbol_by_id(edge["src_id"])
        dst = self._symbol_by_id(edge["dst_id"])
        if not src or not dst:
            return None
        return {
            "type": edge["edge_type"],
            "source": {
                "id": src["id"],
                "name": src["name"],
                "repo_path": src["repo_path"],
            },
            "target": {
                "id": dst["id"],
                "name": dst["name"],
                "repo_path": dst["repo_path"],
            },
        }


AGTAG_METADATA = """"""
