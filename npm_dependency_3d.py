from __future__ import annotations

import argparse
import math
import sys
from itertools import count
from pathlib import Path

import matplotlib

if "--no-show" in sys.argv:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation

from npm_graph_core import (
    NpmRegistryClient,
    analyze_graph_metrics,
    build_dependency_graph,
    compute_3d_layout,
    node_color,
    node_size,
)


def _build_geometry(graph, positions: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray, np.ndarray]:
    ordered_nodes = list(graph.nodes())
    nodes = np.array([positions[node] for node in ordered_nodes], dtype=float)

    if graph.number_of_edges() == 0:
        edges = np.empty((0, 2, 3), dtype=float)
    else:
        edges = np.array([(positions[source], positions[target]) for source, target in graph.edges()], dtype=float)

    return ordered_nodes, nodes, edges


def _set_axes_bounds(ax: plt.Axes, nodes: np.ndarray) -> None:
    center = nodes.mean(axis=0)
    spread = np.ptp(nodes, axis=0).max() / 2
    radius = max(float(spread), 0.7)

    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))


def _print_metric_ranking(title: str, entries: object) -> None:
    print(title)

    if not isinstance(entries, list) or not entries:
        print("  - Veri yok")
        return

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "-"))
        value = float(entry.get("value", 0.0))
        print(f"  - {name}: {value:.4f}")


def animate_dependency_graph(
    graph,
    package_name: str,
    metrics: dict[str, object],
    frames: int,
    interval: int,
    save_path: Path | None,
    show_plot: bool,
) -> Path | None:
    positions = compute_3d_layout(graph, package_name)
    ordered_nodes, nodes, edges = _build_geometry(graph, positions)
    node_sizes = [node_size(graph, node_name) for node_name in ordered_nodes]
    node_colors = [node_color(int(graph.nodes[node_name].get("depth", 0))) for node_name in ordered_nodes]
    label_font_size = max(6.0, 10.5 - graph.number_of_nodes() * 0.08)

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")
    fig.tight_layout()
    density_percent = float(metrics.get("density_percent", 0.0))
    root_betweenness = float(metrics.get("root_betweenness", 0.0))
    root_closeness = float(metrics.get("root_closeness", 0.0))

    def init() -> None:
        ax.clear()
        ax.scatter(
            nodes[:, 0],
            nodes[:, 1],
            nodes[:, 2],
            s=node_sizes,
            c=node_colors,
            alpha=0.9,
            ec="w",
            linewidth=0.6,
            depthshade=True,
        )

        for edge in edges:
            ax.plot(edge[:, 0], edge[:, 1], edge[:, 2], color="#94a3b8", alpha=0.65, linewidth=1.0)

        for node_name, coords in zip(ordered_nodes, nodes):
            ax.text(coords[0], coords[1], coords[2], node_name, fontsize=label_font_size, color="#1f2937")

        _set_axes_bounds(ax, nodes)
        ax.set_title(f"{package_name} npm bagimlilik agi", pad=18)
        ax.text2D(
            0.02,
            0.95,
            f"Dugum: {graph.number_of_nodes()} | Kenar: {graph.number_of_edges()}",
            transform=ax.transAxes,
        )
        ax.text2D(
            0.02,
            0.91,
            f"Yogunluk: %{density_percent:.2f} | Kok betweenness: {root_betweenness:.4f} | Kok closeness: {root_closeness:.4f}",
            transform=ax.transAxes,
        )
        ax.grid(False)
        ax.set_axis_off()

    def frame_update(idx: int) -> None:
        ax.view_init(18 + 4 * math.sin(idx / 28), (idx * 0.85) % 360)

    frame_source = count() if show_plot and save_path is None else range(frames)
    anim = animation.FuncAnimation(
        fig,
        func=frame_update,
        init_func=init,
        interval=interval,
        cache_frame_data=False,
        frames=frame_source,
        repeat=save_path is not None,
    )

    saved_path: Path | None = None
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        writer = animation.PillowWriter(fps=max(1, round(1000 / interval)))
        anim.save(save_path, writer=writer)
        saved_path = save_path

    if show_plot:
        plt.show()

    plt.close(fig)
    return saved_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bir npm paketinin bagimliliklarini cekip matplotlib ile surekli donen 3B animasyon olarak gosterir."
    )
    parser.add_argument("package_name", help="Ornek: express, vite, webpack")
    parser.add_argument("--depth", type=int, default=3, help="Bagimlilik derinligi")
    parser.add_argument("--max-children", type=int, default=8, help="Her dugum icin en fazla bagimlilik")
    parser.add_argument("--max-nodes", type=int, default=30, help="Toplam dugum siniri")
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Opsiyonel GIF cikti dosyasi. Canli ve kesintisiz donus icin kaydetmeden calistirin.",
    )
    parser.add_argument("--frames", type=int, default=360, help="Kaydedilecek animasyondaki frame sayisi")
    parser.add_argument("--interval", type=int, default=40, help="Frame araligi (ms)")
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Matplotlib penceresini acma; genelde --save ile birlikte kullanilir.",
    )
    args = parser.parse_args()

    if args.no_show and args.save is None:
        parser.error("--no-show kullaniliyorsa animasyonu kaydetmek icin --save da verilmelidir.")

    return args


def main() -> None:
    args = parse_args()
    client = NpmRegistryClient()
    graph = build_dependency_graph(
        package_name=args.package_name,
        max_depth=max(args.depth, 1),
        max_children=max(args.max_children, 1),
        max_nodes=max(args.max_nodes, 2),
        client=client,
    )
    metrics = analyze_graph_metrics(graph, root_name=args.package_name)
    saved_path = animate_dependency_graph(
        graph=graph,
        package_name=args.package_name,
        metrics=metrics,
        frames=max(args.frames, 1),
        interval=max(args.interval, 1),
        save_path=args.save,
        show_plot=not args.no_show,
    )

    if saved_path is not None:
        print(f"Animasyon kaydedildi: {saved_path}")

    if not args.no_show:
        print("Matplotlib penceresi acildi ve animasyon surekli donuyor.")

    print(f"Dugum sayisi: {graph.number_of_nodes()} | Kenar sayisi: {graph.number_of_edges()}")
    print(f"Ag yogunlugu: %{float(metrics.get('density_percent', 0.0)):.2f}")
    print(
        "Kok paket merkeziyetleri: "
        f"betweenness={float(metrics.get('root_betweenness', 0.0)):.4f} | "
        f"closeness={float(metrics.get('root_closeness', 0.0)):.4f}"
    )
    _print_metric_ranking("En yuksek betweenness centrality:", metrics.get("top_betweenness", []))
    _print_metric_ranking("En yuksek closeness centrality:", metrics.get("top_closeness", []))


if __name__ == "__main__":
    main()