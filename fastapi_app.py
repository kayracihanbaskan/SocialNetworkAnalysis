from __future__ import annotations

import json
from html import escape

import requests
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from npm_graph_core import NpmRegistryClient, build_dependency_graph, build_plotly_payload


app = FastAPI(title="npm Dependency Graph Explorer")


def load_graph_payload(package_name: str, depth: int, max_children: int, max_nodes: int) -> dict[str, object]:
    client = NpmRegistryClient()
    graph = build_dependency_graph(
        package_name=package_name,
        max_depth=max(depth, 1),
        max_children=max(max_children, 1),
        max_nodes=max(max_nodes, 2),
        client=client,
    )
    payload = build_plotly_payload(graph, package_name)
    payload.update(
        {
            "depth": depth,
            "max_children": max_children,
            "max_nodes": max_nodes,
        }
    )
    return payload


def render_page(
    package_name: str,
    depth: int,
    max_children: int,
    max_nodes: int,
    payload: dict[str, object] | None,
    error_message: str | None,
) -> str:
    graph_json = json.dumps(payload) if payload is not None else "null"
    error_html = f'<p class="error">{escape(error_message)}</p>' if error_message else ""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>npm Bagimlilik Agi</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3efe6;
      --panel: #fffdf8;
      --line: #d7cfbf;
      --text: #1f2937;
      --accent: #c44536;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(212, 168, 98, 0.22), transparent 28%),
        radial-gradient(circle at bottom right, rgba(43, 108, 176, 0.18), transparent 24%),
        var(--bg);
    }}
    main {{
      min-height: 100vh;
      padding: 24px;
      display: grid;
      place-items: center;
    }}
    .panel {{
      width: min(1200px, 100%);
      background: rgba(255, 253, 248, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 80px rgba(31, 41, 55, 0.12);
      padding: 24px;
      backdrop-filter: blur(8px);
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: clamp(30px, 4vw, 52px);
      font-weight: 600;
      letter-spacing: -0.03em;
    }}
    p.lead {{
      margin: 0 0 18px;
      max-width: 70ch;
      line-height: 1.5;
    }}
    form {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr)) auto;
      gap: 12px;
      align-items: end;
      margin-bottom: 16px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 14px;
    }}
    input {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fff;
      font: inherit;
    }}
    button {{
      padding: 12px 18px;
      border: 0;
      border-radius: 14px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
    }}
    .stats {{
      margin: 0 0 16px;
      font-size: 15px;
    }}
    .controls {{
      margin: 0 0 16px;
      font-size: 14px;
      color: #4b5563;
    }}
    .error {{
      color: #8f1d21;
      font-weight: 600;
    }}
    #graph {{
      width: 100%;
      height: min(78vh, 820px);
      border-radius: 20px;
      overflow: hidden;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(215, 207, 191, 0.9);
    }}
    @media (max-width: 900px) {{
      form {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    @media (max-width: 620px) {{
      form {{
        grid-template-columns: 1fr;
      }}
      #graph {{
        height: 65vh;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="panel">
      <h1>npm Bagimlilik Agi</h1>
      <p class="lead">Paket adini girin. Sistem npm registry'den bagimliliklari cekip 20-30 node civarinda 3B bir ag cizer. Grafigi mouse ile istediginiz eksende dondurabilir ve yakinlastirabilirsiniz.</p>
      <form method="get" action="/">
        <label>
          Paket adi
          <input name="package_name" value="{escape(package_name)}" placeholder="express" />
        </label>
        <label>
          Derinlik
          <input name="depth" type="number" min="1" max="5" value="{depth}" />
        </label>
        <label>
          Max children
          <input name="max_children" type="number" min="1" max="12" value="{max_children}" />
        </label>
        <label>
          Max node
          <input name="max_nodes" type="number" min="5" max="80" value="{max_nodes}" />
        </label>
        <button type="submit">Agi Olustur</button>
      </form>
      {error_html}
      <p id="stats" class="stats"></p>
      <p class="controls">Sol tik ile dondur, mouse tekerlegi ile zoom yap, mod bardaki reset tusu ile gorunumu sifirla.</p>
      <div id="graph"></div>
    </section>
  </main>

  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <script>
    const graphData = {graph_json};
    const graphElement = document.getElementById('graph');
    const statsElement = document.getElementById('stats');

    if (graphData) {{
      statsElement.textContent = `Dugum: ${{graphData.node_count}} | Kenar: ${{graphData.edge_count}} | Derinlik: ${{graphData.depth}} | Max node: ${{graphData.max_nodes}}`;

      const edgeTrace = {{
        type: 'scatter3d',
        mode: 'lines',
        x: graphData.edge_x,
        y: graphData.edge_y,
        z: graphData.edge_z,
        hoverinfo: 'none',
        line: {{ color: '#94a3b8', width: 3 }}
      }};

      const nodeTrace = {{
        type: 'scatter3d',
        mode: 'markers+text',
        x: graphData.node_x,
        y: graphData.node_y,
        z: graphData.node_z,
        text: graphData.node_labels,
        textposition: 'top center',
        textfont: {{ size: 10, color: '#1f2937' }},
        hovertext: graphData.hover_text,
        hoverinfo: 'text',
        marker: {{
          size: graphData.node_sizes,
          color: graphData.node_colors,
          opacity: 0.95,
          line: {{ color: '#ffffff', width: 1.4 }}
        }}
      }};

      const layout = {{
        title: `${{graphData.package_name}} npm bagimlilik agi`,
        paper_bgcolor: '#fffdf8',
        plot_bgcolor: '#fffdf8',
        margin: {{ l: 0, r: 0, b: 0, t: 48 }},
        showlegend: false,
        scene: {{
          dragmode: 'orbit',
          xaxis: {{ visible: false }},
          yaxis: {{ visible: false }},
          zaxis: {{ visible: false }},
          camera: {{ eye: {{ x: 1.9, y: 1.9, z: 1.1 }} }}
        }}
      }};

      Plotly.newPlot(graphElement, [edgeTrace, nodeTrace], layout, {{
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        scrollZoom: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
      }});
    }} else {{
      statsElement.textContent = 'Bir paket adi girip agi olusturun.';
    }}
  </script>
</body>
</html>
"""


@app.get("/api/graph")
def graph_api(
    package_name: str = Query(default="express"),
    depth: int = Query(default=3, ge=1, le=5),
    max_children: int = Query(default=8, ge=1, le=12),
    max_nodes: int = Query(default=30, ge=5, le=80),
) -> dict[str, object]:
    return load_graph_payload(package_name, depth, max_children, max_nodes)


@app.get("/", response_class=HTMLResponse)
def home(
    package_name: str = Query(default="express"),
    depth: int = Query(default=3, ge=1, le=5),
    max_children: int = Query(default=8, ge=1, le=12),
    max_nodes: int = Query(default=30, ge=5, le=80),
) -> HTMLResponse:
    payload: dict[str, object] | None = None
    error_message: str | None = None

    try:
        payload = load_graph_payload(package_name, depth, max_children, max_nodes)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            error_message = f"'{package_name}' isminde bir npm paketi bulunamadi."
        else:
            error_message = f"npm verisi cekilirken hata olustu: {exc}"
    except Exception as exc:
        error_message = f"Graph olusturulamadi: {exc}"

    return HTMLResponse(render_page(package_name, depth, max_children, max_nodes, payload, error_message))