from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from urllib.parse import quote

import networkx as nx
import numpy as np
import requests


REGISTRY_URL = "https://registry.npmjs.org"
DEPTH_PALETTE = {
    0: "#d1495b",
    1: "#edae49",
    2: "#66a182",
    3: "#2e4057",
    4: "#5f0f40",
}
DEFAULT_NODE_COLOR = "#6c757d"


@dataclass
class PackageNode:
    name: str
    resolved_version: str
    requested_version: str
    depth: int


class NpmRegistryClient:
    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.document_cache: dict[str, dict] = {}
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "SocialNetworkAnalysis/1.0",
            }
        )

    def fetch_package_document(self, package_name: str) -> dict:
        if package_name in self.document_cache:
            return self.document_cache[package_name]

        response = self.session.get(
            f"{REGISTRY_URL}/{quote(package_name, safe='@')}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        document = response.json()
        self.document_cache[package_name] = document
        return document

    def fetch_package_version(self, package_name: str, requested_version: str = "latest") -> PackageNode:
        document = self.fetch_package_document(package_name)
        versions = document.get("versions", {})
        dist_tags = document.get("dist-tags", {})

        if requested_version == "latest":
            resolved_version = dist_tags.get("latest")
        else:
            resolved_version = requested_version if requested_version in versions else dist_tags.get("latest")

        if not resolved_version or resolved_version not in versions:
            raise ValueError(f"'{package_name}' paketi icin surum bulunamadi.")

        return PackageNode(
            name=package_name,
            resolved_version=resolved_version,
            requested_version=requested_version,
            depth=0,
        )

    def fetch_dependencies(self, package_name: str, resolved_version: str) -> dict[str, str]:
        document = self.fetch_package_document(package_name)
        version_data = document.get("versions", {}).get(resolved_version, {})
        dependencies = version_data.get("dependencies", {})
        return dict(sorted(dependencies.items(), key=lambda item: item[0].lower()))


def build_dependency_graph(
    package_name: str,
    max_depth: int,
    max_children: int,
    max_nodes: int,
    client: NpmRegistryClient,
) -> nx.DiGraph:
    root = client.fetch_package_version(package_name)
    graph = nx.DiGraph()
    graph.add_node(
        root.name,
        label=root.name,
        depth=0,
        resolved_version=root.resolved_version,
        requested_version=root.requested_version,
    )

    queue: deque[tuple[str, int]] = deque([(root.name, 0)])
    visited_expansions: set[str] = set()

    while queue and graph.number_of_nodes() < max_nodes:
        current_name, current_depth = queue.popleft()

        if current_name in visited_expansions or current_depth >= max_depth:
            continue

        visited_expansions.add(current_name)
        current_version = graph.nodes[current_name]["resolved_version"]

        try:
            dependencies = client.fetch_dependencies(current_name, current_version)
        except Exception:
            continue

        for dependency_name, requested_version in list(dependencies.items())[:max_children]:
            if graph.number_of_nodes() >= max_nodes and dependency_name not in graph:
                break

            try:
                dependency_node = client.fetch_package_version(dependency_name, requested_version)
            except Exception:
                dependency_node = PackageNode(
                    name=dependency_name,
                    resolved_version="unknown",
                    requested_version=requested_version,
                    depth=current_depth + 1,
                )

            if dependency_name not in graph:
                graph.add_node(
                    dependency_name,
                    label=dependency_name,
                    depth=current_depth + 1,
                    resolved_version=dependency_node.resolved_version,
                    requested_version=dependency_node.requested_version,
                )

            graph.add_edge(current_name, dependency_name, requested_version=requested_version)

            if current_depth + 1 < max_depth:
                queue.append((dependency_name, current_depth + 1))

    return graph


def node_color(depth: int) -> str:
    return DEPTH_PALETTE.get(depth, DEFAULT_NODE_COLOR)


def node_size(graph: nx.DiGraph, node_name: str) -> float:
    degree = graph.degree(node_name)
    depth = int(graph.nodes[node_name].get("depth", 0))
    size = 120 + math.log2(degree + 2) * 70
    if depth == 0:
        size *= 1.7
    return size


def compute_3d_layout(graph: nx.DiGraph, root_name: str) -> dict[str, np.ndarray]:
    if graph.number_of_nodes() == 1:
        return {root_name: np.array([0.0, 0.0, 0.0])}

    try:
        positions = nx.spring_layout(
            graph,
            dim=3,
            seed=25519,
            k=1.5 / math.sqrt(max(graph.number_of_nodes(), 2)),
            iterations=300,
            method="energy",
        )
    except TypeError:
        positions = nx.spring_layout(
            graph,
            dim=3,
            seed=25519,
            k=1.5 / math.sqrt(max(graph.number_of_nodes(), 2)),
            iterations=300,
        )

    return {node: np.asarray(coords, dtype=float) for node, coords in positions.items()}


def build_plotly_payload(graph: nx.DiGraph, package_name: str) -> dict[str, object]:
    positions = compute_3d_layout(graph, package_name)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    edge_z: list[float | None] = []

    for source, target in graph.edges():
        x0, y0, z0 = positions[source]
        x1, y1, z1 = positions[target]
        edge_x.extend([float(x0), float(x1), None])
        edge_y.extend([float(y0), float(y1), None])
        edge_z.extend([float(z0), float(z1), None])

    node_x: list[float] = []
    node_y: list[float] = []
    node_z: list[float] = []
    node_labels: list[str] = []
    node_sizes: list[float] = []
    node_colors: list[str] = []
    hover_text: list[str] = []

    for node_name, node_data in graph.nodes(data=True):
        x, y, z = positions[node_name]
        degree = graph.degree(node_name)
        depth = int(node_data.get("depth", 0))
        node_x.append(float(x))
        node_y.append(float(y))
        node_z.append(float(z))
        node_labels.append(node_name)
        node_sizes.append(max(8.0, round(node_size(graph, node_name) / 18, 2)))
        node_colors.append(node_color(depth))
        hover_text.append(
            "<br>".join(
                [
                    f"Paket: {node_name}",
                    f"Cozulen surum: {node_data.get('resolved_version', 'unknown')}",
                    f"Istenen surum: {node_data.get('requested_version', 'latest')}",
                    f"Derinlik: {depth}",
                    f"Derece: {degree}",
                ]
            )
        )

    return {
        "package_name": package_name,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "edge_x": edge_x,
        "edge_y": edge_y,
        "edge_z": edge_z,
        "node_x": node_x,
        "node_y": node_y,
        "node_z": node_z,
        "node_labels": node_labels,
        "node_sizes": node_sizes,
        "node_colors": node_colors,
        "hover_text": hover_text,
    }