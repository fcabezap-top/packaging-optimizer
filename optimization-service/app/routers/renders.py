"""
Render endpoints — return self-contained HTML with interactive Plotly 3-D figures.

Each endpoint is protected with the same reviewer/admin JWT requirement as the
rest of the service.  The caller (frontend) fetches the HTML with an Authorization
header and injects it into an <iframe srcdoc="...">.

Current endpoints
-----------------
GET /renders/container/{container_id}
    Two-box 3-D render of a container's dimension ranges:
      • outer box  = (length.max, height.max, width.max)  — light gray, transparent
      • inner box  = (length.min, height.min, width.min)  — dark, more opaque
    Dimension annotations (L / H / W) show the full min–max range in cm.
"""

from __future__ import annotations

from typing import List

import plotly.graph_objects as go
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..database import containers_collection, rules_collection
from ..security import TokenData, require_reviewer_or_admin

router = APIRouter(prefix="/renders", tags=["Renders"])


# ── Geometry helpers (adapted from reference Render3d.py) ─────────────────────

def _box_faces(
    x: float, y: float, z: float,
    dx: float, dy: float, dz: float,
    name: str,
    opacity: float = 0.15,
    color: str = "#a0a0a0",
    showlegend: bool = True,
) -> List:
    """Six clean rectangular faces via go.Surface — no diagonal lines."""
    x1, y1, z1 = x + dx, y + dy, z + dz

    def _face(xs, ys, zs, first: bool = False) -> go.Surface:
        return go.Surface(
            x=xs, y=ys, z=zs,
            opacity=opacity,
            colorscale=[[0, color], [1, color]],
            showscale=False,
            hoverinfo="skip",
            name=name if first else "",
            showlegend=(showlegend if first else False),
        )

    return [
        _face([[x, x1],[x, x1]], [[y,  y ],[y1, y1]], [[z,  z ],[z,  z ]], first=True),  # bottom
        _face([[x, x1],[x, x1]], [[y,  y ],[y1, y1]], [[z1, z1],[z1, z1]]),               # top
        _face([[x, x1],[x, x1]], [[y,  y ],[y,  y ]], [[z,  z ],[z1, z1]]),               # front
        _face([[x, x1],[x, x1]], [[y1, y1],[y1, y1]], [[z,  z ],[z1, z1]]),               # back
        _face([[x,  x],[x,  x]], [[y,  y1],[y,  y1]], [[z,  z ],[z1, z1]]),               # left
        _face([[x1,x1],[x1,x1]], [[y,  y1],[y,  y1]], [[z,  z ],[z1, z1]]),               # right
    ]


def _box_edges(
    x: float, y: float, z: float,
    dx: float, dy: float, dz: float,
    name: str,
    width: float = 2,
    color: str = "#888888",
) -> go.Scatter3d:
    """Clean wireframe edges — no diagonal jumps."""
    x1, y1, z1 = x + dx, y + dy, z + dz
    segs = [
        [(x,  y,  z ), (x1, y,  z ), (x1, y1, z ), (x,  y1, z ), (x,  y,  z )],   # bottom
        [(x,  y,  z1), (x1, y,  z1), (x1, y1, z1), (x,  y1, z1), (x,  y,  z1)],   # top
        [(x,  y,  z ), (x,  y,  z1)],   # edge left-front
        [(x1, y,  z ), (x1, y,  z1)],   # edge right-front
        [(x1, y1, z ), (x1, y1, z1)],   # edge right-back
        [(x,  y1, z ), (x,  y1, z1)],   # edge left-back
    ]
    xs: list = []; ys: list = []; zs: list = []
    for seg in segs:
        for p in seg:
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
        xs.append(None); ys.append(None); zs.append(None)
    return go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="lines",
        line=dict(width=width, color=color),
        name=name,
        showlegend=False,
        hoverinfo="skip",
    )


def _orientation_arrow_z(
    ax: float, ay: float, z_base: float, z_tip: float,
    color: str, width: float = 3,
    label_line1: str = "", label_line2: str = "",
) -> List:
    """Arrow pointing up (Z+) drawn with Scatter3d lines + optional two-line label."""
    arm = (z_tip - z_base) * 0.22
    mid_z = (z_base + z_tip) / 2
    span  = z_tip - z_base
    traces: list = [
        go.Scatter3d(
            x=[ax, ax], y=[ay, ay], z=[z_base, z_tip],
            mode="lines", line=dict(color=color, width=width),
            showlegend=False, hoverinfo="skip",
        ),
        go.Scatter3d(
            x=[ax - arm, ax, ax + arm],
            y=[ay,        ay, ay      ],
            z=[z_tip - arm, z_tip, z_tip - arm],
            mode="lines", line=dict(color=color, width=width),
            showlegend=False, hoverinfo="skip",
        ),
    ]
    if label_line1:
        traces.append(go.Scatter3d(
            x=[ax], y=[ay], z=[mid_z + span * 0.10],
            mode="text", text=[label_line1],
            textfont=dict(color=color, size=11, family="'Inter', Arial"),
            textposition="middle left",
            showlegend=False, hoverinfo="skip",
        ))
    if label_line2:
        traces.append(go.Scatter3d(
            x=[ax], y=[ay], z=[mid_z - span * 0.10],
            mode="text", text=[label_line2],
            textfont=dict(color=color, size=11, family="'Inter', Arial"),
            textposition="middle left",
            showlegend=False, hoverinfo="skip",
        ))
    return traces


def _orientation_arrow_y(
    ax: float, y_base: float, y_tip: float, az: float,
    color: str, width: float = 3,
    label_line1: str = "", label_line2: str = "",
) -> List:
    """Arrow pointing forward (Y+) drawn with Scatter3d lines + optional two-line label."""
    arm = (y_tip - y_base) * 0.22
    mid_y = (y_base + y_tip) / 2
    span  = y_tip - y_base
    traces: list = [
        go.Scatter3d(
            x=[ax, ax], y=[y_base, y_tip], z=[az, az],
            mode="lines", line=dict(color=color, width=width),
            showlegend=False, hoverinfo="skip",
        ),
        go.Scatter3d(
            x=[ax - arm, ax,        ax + arm],
            y=[y_tip - arm, y_tip,  y_tip - arm],
            z=[az,          az,     az          ],
            mode="lines", line=dict(color=color, width=width),
            showlegend=False, hoverinfo="skip",
        ),
    ]
    if label_line1:
        z_off = (y_tip - y_base) * 0.14
        mid_y_val = (y_base + y_tip) / 2
        traces.append(go.Scatter3d(
            x=[ax], y=[mid_y_val], z=[az + z_off],
            mode="text", text=[label_line1],
            textfont=dict(color=color, size=11, family="'Inter', Arial"),
            textposition="middle left",
            showlegend=False, hoverinfo="skip",
        ))
    if label_line2:
        z_off = (y_tip - y_base) * 0.14
        mid_y_val = (y_base + y_tip) / 2
        traces.append(go.Scatter3d(
            x=[ax], y=[mid_y_val], z=[az - z_off],
            mode="text", text=[label_line2],
            textfont=dict(color=color, size=11, family="'Inter', Arial"),
            textposition="middle left",
            showlegend=False, hoverinfo="skip",
        ))
    return traces


def _dim_annotations_range(
    L_min: float, L_max: float,
    H_min: float, H_max: float,
    W_min: float, W_max: float,
    line_color: str = "#999999",
    text_color: str = "#333333",
    font_size: int = 13,
) -> List[go.Scatter3d]:
    """
    Dimension annotation traces showing L / H / W ranges.
    Positions follow the same convention as the reference PDF renderer:
      H  → right-front edge  (x=L_max, y=0),  vertical   z 0→H_max
      W  → right-front edge  (x=L_max, z=―),  horizontal y 0→W_max
      L  → back-bottom edge  (y=W_max, z=―),  horizontal x 0→L_max
    """
    L, W, H = L_max, W_max, H_max
    gap  = max(L, W, H) * 0.10
    tick = gap * 0.25
    traces: List[go.Scatter3d] = []

    def _line(xs, ys, zs, label, tx, ty, tz, tpos="middle right") -> None:
        traces.append(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="lines",
            line=dict(color=line_color, width=2),
            showlegend=False, hoverinfo="skip",
        ))
        traces.append(go.Scatter3d(
            x=[tx], y=[ty], z=[tz], mode="text",
            text=[label],
            textfont=dict(color=text_color, size=font_size, family="'Inter', Arial"),
            textposition=tpos,
            showlegend=False, hoverinfo="skip",
        ))

    def _tick_pair(axis, a_vals, b0, b1, c0):
        for a in a_vals:
            kw = dict(mode="lines", line=dict(color=line_color, width=2),
                      showlegend=False, hoverinfo="skip")
            if axis == "x":
                traces.append(go.Scatter3d(x=[a, a], y=[b0, b1], z=[c0, c0], **kw))
            elif axis == "y":
                traces.append(go.Scatter3d(x=[b0, b1], y=[a, a], z=[c0, c0], **kw))
            elif axis == "z":
                traces.append(go.Scatter3d(x=[b0, b1], y=[c0, c0], z=[a, a], **kw))

    def _label(lo: float, hi: float, unit: str = "cm") -> str:
        if lo == hi:
            return f"{lo:.0f} {unit}"
        return f"{lo:.0f}–{hi:.0f} {unit}"

    # ── H: arista derecha frontal ─────────────────────────────────────────
    hx = L + gap * 1.2
    hy = 0.0
    _line([hx, hx], [hy, hy], [0, H],
          f"H  {_label(H_min, H_max)}",
          hx, hy, H / 2, "middle left")
    _tick_pair("z", [0, H], hx - tick, hx + tick, hy)

    # ── W: arista derecha frontal (bajo la caja) ──────────────────────────
    wx = L + gap * 1.2
    wz = -gap * 0.7
    _line([wx, wx], [0, W], [wz, wz],
          f"W  {_label(W_min, W_max)}",
          wx + tick, W / 2, wz, "middle right")
    _tick_pair("y", [0, W], wx - tick, wx + tick, wz)

    # ── L: arista trasera inferior ────────────────────────────────────────
    ly = W + gap * 1.2
    lz = -gap * 0.7
    _line([0, L], [ly, ly], [lz, lz],
          f"L  {_label(L_min, L_max)}",
          L / 2, ly + tick, lz, "bottom center")
    _tick_pair("x", [0, L], ly - tick, ly + tick, lz)

    return traces


def _build_container_figure(doc: dict) -> go.Figure:
    dims  = doc["dims_cm"]
    L_min = dims["length"]["min"];  L_max = dims["length"]["max"]
    H_min = dims["height"]["min"];  H_max = dims["height"]["max"]
    W_min = dims["width"]["min"];   W_max = dims["width"]["max"]
    name  = doc["name"]
    wall_cm = doc.get("wall_thickness_mm", 0) / 10.0

    traces = []

    # Outer box — solo contorno, sin relleno
    traces.append(_box_edges(0, 0, 0, L_max, W_max, H_max,
                              f"{name} — máx", width=2, color="#1a73e8"))

    # Inner box — min dims — solo contorno + relleno útil (igual que el máx)
    all_fixed = (L_min == L_max and H_min == H_max and W_min == W_max)
    if not all_fixed:
        traces.append(_box_edges(0, 0, 0, L_min, W_min, H_min,
                                  f"{name} — mín", width=2.5, color="#2E7D61"))
        if wall_cm > 0:
            iL_min = max(L_min - 2 * wall_cm, 0)
            iW_min = max(W_min - 2 * wall_cm, 0)
            iH_min = max(H_min - 2 * wall_cm - 1.0, 0)
            traces.extend(_box_faces(wall_cm, wall_cm, wall_cm, iL_min, iW_min, iH_min,
                                      f"{name} — mín interior útil",
                                      opacity=0.15, color="#34A883"))
        else:
            traces.extend(_box_faces(0, 0, 0, L_min, W_min, H_min,
                                      f"{name} — mín", opacity=0.15, color="#34A883"))

    # Espacio útil — azul con relleno (descontando paredes y solapa 1 cm arriba)
    if wall_cm > 0:
        iL = max(L_max - 2 * wall_cm, 0)
        iW = max(W_max - 2 * wall_cm, 0)
        iH = max(H_max - 2 * wall_cm - 1.0, 0)
        traces.extend(_box_faces(wall_cm, wall_cm, wall_cm, iL, iW, iH,
                                  f"Interior útil (pared {doc['wall_thickness_mm']:.0f} mm · solapa 1 cm)",
                                  opacity=0.25, color="#4da3ff"))
        traces.append(_box_edges(wall_cm, wall_cm, wall_cm, iL, iW, iH,
                                  "Contorno interior útil", width=2, color="#1a73e8"))
    else:
        # Sin grosor definido: azul sobre el exterior completo (comportamiento original)
        traces.extend(_box_faces(0, 0, 0, L_max, W_max, H_max,
                                  f"{name} — máx", opacity=0.25, color="#4da3ff"))

    # Dimension annotations
    traces += _dim_annotations_range(L_min, L_max, H_min, H_max, W_min, W_max)

    # Camera: esquina frontal-derecha, cotas H/W visibles (eye positivo x e y)
    # center z negativo sube la caja dentro del viewport (elimina hueco blanco)
    camera = dict(
        eye=dict(x=1.1, y=0.9, z=0.55),
        center=dict(x=0, y=0, z=-0.15),
        up=dict(x=0, y=0, z=1),
    )

    pad = max(L_max, W_max, H_max) * 0.25
    _axis_clean = dict(
        title="",
        showgrid=False, zeroline=False,
        showticklabels=False, showaxeslabels=False,
        showbackground=False, showline=False, showspikes=False,
    )
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=None,
        paper_bgcolor="white",
        plot_bgcolor="white",
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="right",  x=1,
            font=dict(family="'Inter', Arial, sans-serif", size=12),
        ),
        scene=dict(
            domain=dict(x=[0, 1], y=[0, 1]),
            camera=camera,
            xaxis=dict(**_axis_clean, range=[-pad * 0.3, L_max + pad]),
            yaxis=dict(**_axis_clean, range=[-pad * 0.3, W_max + pad]),
            zaxis=dict(**_axis_clean, range=[-pad * 0.4, H_max + pad]),
            aspectmode="data",
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ── Constraint figure ────────────────────────────────────────────────────────

def _build_constraint_figure(rule_doc: dict) -> go.Figure:
    """3-D visual for a global rule constraint (orientation or stacking)."""
    constraint = rule_doc.get("constraint", {})
    orientation_locked = constraint.get("orientation_locked", False)
    locked_axis        = constraint.get("locked_axis")
    max_stack          = constraint.get("max_stack_layers")

    # Same colors as container render — outer=blue, inner=green — both translucent
    BLUE_FILL  = "#4da3ff"
    BLUE_EDGE  = "#1a73e8"
    GREEN_FILL = "#34A883"
    GREEN_EDGE = "#2E7D61"

    traces: list = []

    # Box proportions based on constraint semantics
    if orientation_locked and locked_axis == "height":
        bL, bW, bH = 8.0, 8.0, 15.0     # tall, upright (33% shorter for display)
    elif orientation_locked:             # width / length / None
        bL, bW, bH = 20.0, 16.0, 7.0   # flat, lying
    else:
        bL, bW, bH = 12.0, 10.0, 14.0  # square-ish for stacking

    if max_stack is not None:
        n   = min(int(max_stack), 3)
        gap = 1.5
        for i in range(n):
            zo      = i * (bH + gap)
            opacity = 0.25 if i == 0 else 0.15
            fill    = BLUE_FILL  if i == 0 else GREEN_FILL
            edge    = BLUE_EDGE  if i == 0 else GREEN_EDGE
            traces.extend(_box_faces(0, 0, zo, bL, bW, bH,
                                     f"Caja interior {i + 1}",
                                     opacity=opacity, color=fill))
            traces.append(_box_edges(0, 0, zo, bL, bW, bH,
                                     f"Contorno {i + 1}",
                                     color=edge, width=2.5))
        total_h = n * bH + (n - 1) * gap
        traces.append(go.Scatter3d(
            x=[bL / 2], y=[-2.5], z=[total_h / 2],
            mode="text",
            text=[f"M\u00e1x. {max_stack} capas"],
            textfont=dict(color="#333333", size=13, family="'Inter', Arial"),
            textposition="middle left",
            showlegend=False, hoverinfo="skip",
        ))
    else:
        traces.extend(_box_faces(0, 0, 0, bL, bW, bH, "Caja interior",
                                  opacity=0.25, color=BLUE_FILL))
        traces.append(_box_edges(0, 0, 0, bL, bW, bH, "Contorno",
                                 color=BLUE_EDGE, width=2.5))

    ARROW_COLOR = "#222222"  # negro

    # Orientation arrow — al lado opuesto al original (bL+gap en X = visualmente izquierda)
    if orientation_locked:
        gap_x = bL * 0.12          # espacio mínimo al lado del box
        ax    = bL + gap_x         # posición X de la flecha (lado opuesto al anterior)
        ay    = bW / 2
        if locked_axis == "height":
            # flecha pequeña: ocupa el 50% central de la altura del box
            z_start = bH * 0.25
            z_end   = bH * 0.75
            traces.extend(_orientation_arrow_z(
                ax, ay, z_start, z_end,
                ARROW_COLOR, width=2,
                label_line1="Orientación",
                label_line2="vertical",
            ))
        else:
            # caja plana — flecha horizontal, 50% central del ancho
            y_start = bW * 0.25
            y_end   = bW * 0.75
            traces.extend(_orientation_arrow_y(
                ax, y_start, y_end,
                bH / 2,
                ARROW_COLOR, width=2,
                label_line1="Orientación",
                label_line2="horizontal",
            ))

    extra_z = max_stack * (bH + 1.5) if max_stack else bH
    pad     = max(bL, bW, extra_z) * 0.38
    # extra espacio a la derecha (3D) para flecha + etiqueta
    right_margin = bL * 0.12 + bL * 0.9 if orientation_locked else pad * 0.3
    _axis_clean = dict(
        title="",
        showgrid=False, zeroline=False,
        showticklabels=False, showaxeslabels=False,
        showbackground=False, showline=False, showspikes=False,
    )
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=None,
        paper_bgcolor="white",
        plot_bgcolor="white",
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="right",  x=1,
            font=dict(family="'Inter', Arial, sans-serif", size=12),
        ),
        scene=dict(
            camera=dict(
                eye=dict(x=1.4, y=0.9, z=0.7),
                center=dict(x=0, y=0, z=-0.1),
                up=dict(x=0, y=0, z=1),
            ),
            xaxis=dict(**_axis_clean, range=[-pad * 0.3, bL + right_margin]),
            yaxis=dict(**_axis_clean, range=[-pad * 0.3, bW + pad * 1.5]),
            zaxis=dict(**_axis_clean, range=[-pad * 0.3, extra_z + pad]),
            aspectmode="data",
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ── Endpoints ─────────────────────────────────────────────────────────────────

def _figure_to_html(fig: go.Figure) -> str:
    """Convert figure to self-contained fullscreen HTML."""
    html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=True,
        config={"responsive": True, "displayModeBar": False},
    )
    inject = (
        "<style>"
        "*{box-sizing:border-box;}"
        "html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;}"
        "body>div{height:100%!important;}"
        ".plotly-graph-div{width:100%!important;height:100%!important;}"
        "</style>"
        "<script>"
        "function _resize(){"
        "  var el=document.querySelector('.plotly-graph-div');"
        "  if(el&&window.Plotly){"
        "    Plotly.relayout(el,{width:window.innerWidth,height:window.innerHeight});"
        "  }"
        "}"
        "window.addEventListener('load',function(){ _resize(); setTimeout(_resize,300); setTimeout(_resize,800); });"
        "window.addEventListener('resize',_resize);"
        "</script>"
    )
    return html.replace("</head>", inject + "</head>", 1)


class PreviewRequest(BaseModel):
    length_min: float
    length_max: float
    height_min: float
    height_max: float
    width_min: float
    width_max: float
    wall_thickness_mm: float = 0.0


@router.post("/preview", response_class=HTMLResponse)
def render_preview(
    req: PreviewRequest,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Render a preview from raw dimensions (no DB lookup)."""
    doc = {
        "name": "Preview",
        "dims_cm": {
            "length": {"min": req.length_min, "max": req.length_max},
            "height": {"min": req.height_min, "max": req.height_max},
            "width":  {"min": req.width_min,  "max": req.width_max},
        },
        "wall_thickness_mm": req.wall_thickness_mm,
    }
    return HTMLResponse(content=_figure_to_html(_build_container_figure(doc)))


@router.get("/rule/{rule_id}", response_class=HTMLResponse)
def render_rule(
    rule_id: str,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """
    Returns a self-contained HTML page with a Plotly 3-D constraint visualisation
    for the given rule (orientation arrow or stacked boxes).
    """
    doc = rules_collection.find_one({"id": rule_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    doc.pop("_id", None)
    return HTMLResponse(content=_figure_to_html(_build_constraint_figure(doc)))


@router.get("/container/{container_id}", response_class=HTMLResponse)
def render_container(
    container_id: str,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """
    Returns a self-contained HTML page with a Plotly 3-D render of the
    selected container's dimension ranges (inner = min, outer = max box).
    """
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    doc.pop("_id", None)
    return HTMLResponse(content=_figure_to_html(_build_container_figure(doc)))
