"""
Genera el PDF de propuesta de packaging en base64.

Adaptado del sistema de referencia para trabajar con el dict `doc` de MongoDB
en lugar del modelo de dominio PackagingProposal.

Dependencias: reportlab, matplotlib, Pillow (ya en requirements.txt)
"""
# NOTE: full rewrite — Spanish labels, product header, articles in inner PNG, 3-column layout

from __future__ import annotations

import base64
import io
import logging
import re
from typing import Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import landscape as rl_landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm as rl_cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import Image as RLImage
from PIL import Image as PILImage

log = logging.getLogger("pdf_builder")

# ── Paleta ────────────────────────────────────────────────────────────────────
_BLACK   = rl_colors.HexColor("#000000")
_GREY33  = rl_colors.HexColor("#333333")
_GREY66  = rl_colors.HexColor("#666666")
_GREYCC  = rl_colors.HexColor("#CCCCCC")
_GREYE0  = rl_colors.HexColor("#E0E0E0")

# ── Disclaimer legal (español) ───────────────────────────────────────────────
_DISCLAIMER = (
    "Esta propuesta de empaque se genera en base a la información de la caja interior "
    "proporcionada por el proveedor. Asegúrese de que dicha información es correcta. "
    "Esta solución sigue todos los puntos obligatorios establecidos en la Normativa "
    "Logística e incorpora requisitos adicionales de todas las áreas de la cadena de "
    "suministro. El cumplimiento de esta propuesta es obligatorio y será verificado en "
    "almacén. Cualquier incumplimiento en dimensiones, peso y/o unidades puede derivar "
    "en penalizaciones por los costes extra generados. Si durante la producción del "
    "embalaje final las dimensiones de la caja maestra superan una tolerancia de +/-1 cm, "
    "o si existen limitaciones técnicas que impidan seguir la propuesta, contacte con "
    "su coordinador de empaque."
)

_HEADER_H_PT = 65
_DISCLAIMER_RESERVED_CM = 0.0

# ── Estilos ───────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    return dict(
        title=ParagraphStyle("ptitle", fontName="Helvetica", fontSize=10,
                             leading=14, textColor=_BLACK, alignment=TA_LEFT,
                             charSpace=1, spaceAfter=0),
        subtitle=ParagraphStyle("psub", fontName="Helvetica", fontSize=8,
                                leading=11, textColor=_GREY66, alignment=TA_LEFT),
        graph_title=ParagraphStyle("pgtitle", fontName="Helvetica", fontSize=8,
                                   leading=11, textColor=_GREY66, alignment=TA_CENTER),
        info_label=ParagraphStyle("pilbl", fontName="Helvetica", fontSize=7,
                                  leading=10, textColor=_GREY66, alignment=TA_LEFT),
        info_value=ParagraphStyle("pival", fontName="Helvetica", fontSize=7,
                                  leading=10, textColor=_GREY33, alignment=TA_LEFT),
    )


# ── Helpers matplotlib ────────────────────────────────────────────────────────

def _parse_color(
    c: Optional[str],
    default_rgb: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    default_alpha: float = 0.3,
) -> Tuple[float, float, float, float]:
    if not c:
        return (*default_rgb, default_alpha)
    c = str(c).strip()
    m = re.match(r"rgba?\((\d+),(\d+),(\d+)(?:,([0-9.]+))?\)", c)
    if m:
        r, g, b = int(m.group(1)) / 255, int(m.group(2)) / 255, int(m.group(3)) / 255
        a = float(m.group(4)) if m.group(4) else default_alpha
        return (r, g, b, a)
    m = re.match(r"#([0-9a-fA-F]{6})", c)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, default_alpha)
    return (*default_rgb, default_alpha)


def _mesh3d_faces(x, y, z, ii, jj, kk):
    return [[(x[i], y[i], z[i]), (x[j], y[j], z[j]), (x[k], y[k], z[k])]
            for i, j, k in zip(ii, jj, kk)]


def _clean_ax3d(ax) -> None:
    ax.set_axis_off()
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("none")
    ax.grid(False)


def _dim_annotation(ax, p1, p2, label, color="#7a7a7a", fontsize=8.0, offset=(0, 0, 0)):
    x1, y1, z1 = p1[0] + offset[0], p1[1] + offset[1], p1[2] + offset[2]
    x2, y2, z2 = p2[0] + offset[0], p2[1] + offset[1], p2[2] + offset[2]
    ax.plot([x1, x2], [y1, y2], [z1, z2], color=color, linewidth=0.9, zorder=10)
    ax.scatter([x1, x2], [y1, y2], [z1, z2], color=color, s=8, marker="|", zorder=11, linewidths=1.0)
    for (ox, oy, oz), (cx, cy, cz) in [(p1, (x1, y1, z1)), (p2, (x2, y2, z2))]:
        ax.plot([ox, cx], [oy, cy], [oz, cz], color=color, linewidth=0.5, linestyle="--", zorder=9, alpha=0.5)
    mx, my, mz = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2
    ax.text(mx, my, mz, label, ha="center", va="center", fontsize=fontsize,
            color="#111111", fontfamily="DejaVu Sans", fontweight="normal", zorder=12,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.9))


_AIR_KEYWORDS = ("air", "void", "aire")


def render_master_png(fig: go.Figure, ext_dims: Tuple[float, float, float], dpi: int = 130) -> bytes:
    L_ext, W_ext, H_ext = ext_dims
    max_dim = max(L_ext, W_ext, H_ext) or 1.0
    fig_w = 7 + 3 * (L_ext / max_dim)
    fig_h = 5 + 3 * (H_ext / max_dim)
    mpl_fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = mpl_fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    mpl_fig.patch.set_facecolor("white")
    _clean_ax3d(ax)

    all_x, all_y, all_z = [], [], []
    for trace in fig.data:
        ttype = trace.type
        is_air = any(k in (trace.name or "").lower() for k in _AIR_KEYWORDS)

        if ttype == "mesh3d":
            x, y, z = list(trace.x or []), list(trace.y or []), list(trace.z or [])
            I2, J2, K2 = list(trace.i or []), list(trace.j or []), list(trace.k or [])
            if not x or not I2:
                continue
            all_x += x; all_y += y; all_z += z
            base_opacity = trace.opacity if trace.opacity is not None else 0.3
            opacity = 0.05 if is_air else base_opacity
            r, g, b, _ = _parse_color(trace.color or None, default_alpha=opacity)
            poly = Poly3DCollection(
                _mesh3d_faces(x, y, z, I2, J2, K2),
                alpha=opacity,
                facecolor=(r, g, b),
                edgecolor=(0.35, 0.35, 0.35, 0.3) if not is_air else (0, 0, 0, 0),
                linewidth=0.3,
            )
            ax.add_collection3d(poly)

        elif ttype == "scatter3d" and "lines" in (trace.mode or ""):
            x_raw = list(trace.x or [])
            y_raw = list(trace.y or [])
            z_raw = list(trace.z or [])
            if not x_raw:
                continue
            all_x += [v for v in x_raw if v is not None]
            all_y += [v for v in y_raw if v is not None]
            all_z += [v for v in z_raw if v is not None]
            lc = trace.line.color if trace.line and trace.line.color else "#888888"
            r, g, b, _ = _parse_color(lc, default_alpha=1.0)
            # Plotly uses None as segment separators → split before passing to matplotlib
            seg_x, seg_y, seg_z = [], [], []
            for xi, yi, zi in zip(x_raw, y_raw, z_raw):
                if xi is None or yi is None or zi is None:
                    if len(seg_x) >= 2:
                        ax.plot(seg_x, seg_y, seg_z,
                                color=(r, g, b), linewidth=0.6,
                                alpha=0.1 if is_air else 0.85)
                    seg_x, seg_y, seg_z = [], [], []
                else:
                    seg_x.append(float(xi))
                    seg_y.append(float(yi))
                    seg_z.append(float(zi))
            if len(seg_x) >= 2:
                ax.plot(seg_x, seg_y, seg_z,
                        color=(r, g, b), linewidth=0.6,
                        alpha=0.1 if is_air else 0.85)

    if all_x and all_y and all_z:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)
        zmin, zmax = 0.0, max(all_z)
        dx = xmax - xmin or 1.0
        dy = ymax - ymin or 1.0
        dz = zmax - zmin or 1.0

        pad = 0.28
        ax.set_xlim(xmin - dx * 0.05, xmax + dx * pad)
        ax.set_ylim(ymin - dy * 0.05, ymax + dy * pad)
        ax.set_zlim(zmin, zmax + dz * 0.15)
        ax.set_box_aspect([dx, dy, dz])

        gap_x = dx * 0.08
        gap_y = dy * 0.08
        gap_z = dz * 0.08
        fs = max(6.0, 8.0 * (6.0 / fig_w))

        lbl_L = f"L  {L_ext:.1f} cm"
        lbl_W = f"W  {W_ext:.1f} cm"
        lbl_H = f"H  {H_ext:.1f} cm"

        _dim_annotation(ax, (xmax, ymin, zmin), (xmax, ymin, zmax), lbl_H,
                        offset=(gap_x * 1.5, -gap_y * 0.3, 0), fontsize=fs)
        _dim_annotation(ax, (xmax, ymin, zmin), (xmax, ymax, zmin), lbl_W,
                        offset=(gap_x * 1.5, gap_y * 0.3, -gap_z * 0.5), fontsize=fs)
        _dim_annotation(ax, (xmin, ymax, zmin), (xmax, ymax, zmin), lbl_L,
                        offset=(0, gap_y * 1.5, -gap_z * 0.5), fontsize=fs)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def _compute_article_grid_in_rotated_inner(
    sm: dict, ib: dict
) -> tuple:
    """
    Returns (nL, nW, nH, art_L, art_W, art_H, wall) in the rotated inner frame,
    where nL/nW/nH are articles per axis and art_L/W/H are article cell sizes (cm).
    """
    inner_axes_used = sm.get("inner_axes_used") or ["max", "med", "min"]
    ib_grid = (ib.get("grid") or [1, 1, 1])
    nmax, nmed, nmin = (list(ib_grid) + [1, 1, 1])[:3]

    int_max = max(ib.get("int_max_cm") or 1.0, 0.1)
    int_med = max(ib.get("int_med_cm") or 1.0, 0.1)
    int_min = max(ib.get("int_min_cm") or 1.0, 0.1)

    grid_for = {
        "max": (nmax, int_max),
        "med": (nmed, int_med),
        "min": (nmin, int_min),
    }
    ax0 = inner_axes_used[0] if len(inner_axes_used) > 0 else "max"
    ax1 = inner_axes_used[1] if len(inner_axes_used) > 1 else "med"
    ax2 = inner_axes_used[2] if len(inner_axes_used) > 2 else "min"

    nL, int_L = grid_for.get(ax0, (1, 1.0))
    nW, int_W = grid_for.get(ax1, (1, 1.0))
    nH, int_H = grid_for.get(ax2, (1, 1.0))

    art_L = int_L / max(nL, 1)
    art_W = int_W / max(nW, 1)
    art_H = int_H / max(nH, 1)
    wall  = (ib.get("wall_thickness_mm") or 3.0) / 10.0
    return nL, nW, nH, art_L, art_W, art_H, wall


def _box_verts(x0, y0, z0, x1, y1, z1):
    return [
        [(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],
        [(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],
        [(x0,y0,z0),(x0,y1,z0),(x0,y1,z1),(x0,y0,z1)],
        [(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)],
        [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0)],
        [(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],
    ]


def render_inner_with_articles_png(
    Lr: float, Wr: float, Hr: float,
    nL: int, nW: int, nH: int,
    art_L: float, art_W: float, art_H: float,
    wall: float,
    dpi: int = 130,
) -> bytes:
    """Renders the inner box (blue) with article grid inside (yellow)."""
    _INNER_FILL = (0x4D/255, 0xA3/255, 0xFF/255)
    _INNER_EDGE = (0x1A/255, 0x73/255, 0xE8/255)
    _ART_FILL   = (0xF5/255, 0xC5/255, 0x18/255)
    _ART_EDGE   = (0xC8/255, 0xA0/255, 0x00/255)

    max_dim = max(Lr, Wr, Hr) or 1.0
    fig_w = max(5.0, 5 + 2 * (Lr / max_dim))
    fig_h = max(5.0, 4 + 2 * (Hr / max_dim))
    mpl_fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = mpl_fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    mpl_fig.patch.set_facecolor("white")
    _clean_ax3d(ax)

    # Inner box shell (transparent)
    inner_verts = _box_verts(0, 0, 0, Lr, Wr, Hr)
    ax.add_collection3d(Poly3DCollection(
        inner_verts, alpha=0.12, facecolor=_INNER_FILL,
        edgecolor=_INNER_EDGE, linewidth=0.9,
    ))

    # Show full grid up to 30 boxes; beyond that scale each axis proportionally
    _MAX_BOXES = 30
    total = nL * nW * nH
    if total <= _MAX_BOXES:
        nL_s, nW_s, nH_s = nL, nW, nH
    else:
        factor = (_MAX_BOXES / total) ** (1 / 3)
        nL_s = max(1, round(nL * factor))
        nW_s = max(1, round(nW * factor))
        nH_s = max(1, round(nH * factor))
    for i in range(nL_s):
        for j in range(nW_s):
            for k in range(nH_s):
                x0 = wall + i * art_L
                y0 = wall + j * art_W
                z0 = wall + k * art_H
                ax.add_collection3d(Poly3DCollection(
                    _box_verts(x0, y0, z0, x0+art_L, y0+art_W, z0+art_H),
                    alpha=0.45, facecolor=_ART_FILL, edgecolor=_ART_EDGE, linewidth=0.4,
                ))

    pad_x, pad_y = Lr * 0.05, Wr * 0.05
    ax.set_xlim(-pad_x, Lr * 1.38)
    ax.set_ylim(-pad_y, Wr * 1.38)
    ax.set_zlim(0, Hr * 1.22)
    ax.set_box_aspect([Lr, Wr, Hr])

    gap_x, gap_y, gap_z = Lr * 0.08, Wr * 0.08, Hr * 0.08
    fs = max(6.0, 8.0 * (5.0 / fig_w))
    _dim_annotation(ax, (Lr,0,0), (Lr,0,Hr),  f"H  {Hr:.1f} cm",
                    offset=(gap_x*1.5, -gap_y*0.3, 0), fontsize=fs)
    _dim_annotation(ax, (Lr,0,0), (Lr,Wr,0),  f"W  {Wr:.1f} cm",
                    offset=(gap_x*1.5,  gap_y*0.3, -gap_z*0.5), fontsize=fs)
    _dim_annotation(ax, (0,Wr,0), (Lr,Wr,0),  f"L  {Lr:.1f} cm",
                    offset=(0, gap_y*1.5, -gap_z*0.5), fontsize=fs)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def render_article_png(a_L: float, a_W: float, a_H: float, dpi: int = 130) -> bytes:
    """Renders a single article box (yellow)."""
    _FILL = (0xF5/255, 0xC5/255, 0x18/255)
    _EDGE = (0xC8/255, 0xA0/255, 0x00/255)

    mpl_fig = plt.figure(figsize=(5.5, 5.5), dpi=dpi)
    ax = mpl_fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    mpl_fig.patch.set_facecolor("white")
    _clean_ax3d(ax)

    ax.add_collection3d(Poly3DCollection(
        _box_verts(0, 0, 0, a_L, a_W, a_H),
        alpha=0.45, facecolor=_FILL, edgecolor=_EDGE, linewidth=0.8,
    ))

    ax.set_xlim(-0.05*a_L, a_L*1.38)
    ax.set_ylim(-0.05*a_W, a_W*1.38)
    ax.set_zlim(0, a_H*1.22)
    ax.set_box_aspect([a_L, a_W, a_H])

    gap_x, gap_y, gap_z = a_L*0.08, a_W*0.08, a_H*0.08
    _dim_annotation(ax, (a_L,0,0),   (a_L,0,a_H),  f"H  {a_H:.1f} cm",
                    offset=(gap_x*1.5, -gap_y*0.3, 0),         fontsize=7.5)
    _dim_annotation(ax, (a_L,0,0),   (a_L,a_W,0),  f"W  {a_W:.1f} cm",
                    offset=(gap_x*1.5,  gap_y*0.3, -gap_z*0.5), fontsize=7.5)
    _dim_annotation(ax, (0,a_W,0),   (a_L,a_W,0),  f"L  {a_L:.1f} cm",
                    offset=(0, gap_y*1.5, -gap_z*0.5),          fontsize=7.5)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


# ── Layout ReportLab ──────────────────────────────────────────────────────────

def _scale_image(png: bytes, max_w: float, max_h: float) -> Tuple[float, float]:
    pil = PILImage.open(io.BytesIO(png))
    pw, ph = pil.size
    scale = min(max_w / pw, max_h / ph)
    return pw * scale, ph * scale


def _kv_row(label: str, value: str, col_w: float, styles: dict) -> Table:
    pad = 0.35 * rl_cm
    t = Table(
        [[Paragraph(label, styles["info_label"]), Paragraph(value, styles["info_value"])]],
        colWidths=[3.5 * rl_cm, col_w - 3.5 * rl_cm - pad - 0.2 * rl_cm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _data_block(rows: list, col_w: float) -> Table:
    lpad = int(0.35 * rl_cm)
    t = Table([[r] for r in rows], colWidths=[col_w - 0.4 * rl_cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), lpad),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _build_header(title: str, styles: dict, product_meta: Optional[dict] = None):
    items = [
        Paragraph(title.upper(), styles["title"]),
        Spacer(1, 0.05 * rl_cm),
    ]
    if product_meta:
        pname = product_meta.get("product_name", "")
        size  = product_meta.get("size_name", "")
        ean   = product_meta.get("ean_code", "")
        if pname:
            items.append(Paragraph(pname, styles["subtitle"]))
        parts = []
        if size: parts.append(f"Talla: {size}")
        if ean:  parts.append(f"EAN: {ean}")
        if parts:
            items.append(Paragraph("  ·  ".join(parts), styles["subtitle"]))
    items += [
        Spacer(1, 0.15 * rl_cm),
        HRFlowable(width="100%", thickness=0.5, color=_GREYCC, spaceAfter=0, spaceBefore=0),
        Spacer(1, 0.2 * rl_cm),
    ]
    return items


def _build_content_block(
    png_master: bytes,
    png_inner: bytes,
    png_article: Optional[bytes],
    doc: dict,
    usable_w: float,
    content_h: float,
    styles: dict,
):
    lpad = int(0.35 * rl_cm)

    sm  = doc.get("selected_master") or {}
    ib  = doc.get("inner_box") or {}
    ad  = doc.get("article_dims") or {}

    master_grid  = sm.get("grid") or [1, 1, 1]
    inners_used  = sm.get("inners_used", 1)
    ext_dims     = sm.get("ext_dims") or [0, 0, 0]
    inner_dims   = sm.get("inner_dims_rotated") or [0, 0, 0]
    nL_m, nW_m, nH_m = (list(master_grid) + [1, 1, 1])[:3]
    L_e, W_e, H_e    = (list(ext_dims)    + [0, 0, 0])[:3]
    Lr, Wr, Hr        = (list(inner_dims)  + [0, 0, 0])[:3]

    total_weight   = sm.get("total_weight_kg", 0)
    inner_w_kg     = total_weight / inners_used if inners_used else 0.0
    container_name = sm.get("container_name", "—")
    lot_size       = doc.get("lot_size", "—")

    a_L  = ad.get("length_cm", 0)
    a_W  = ad.get("width_cm",  0)
    a_H  = ad.get("height_cm", 0)
    a_kg = ad.get("weight_kg", 0)

    ib_grid = ib.get("grid") or [1, 1, 1]
    n_arts  = ib_grid[0] * ib_grid[1] * ib_grid[2]
    nL_r, nW_r, nH_r, *_ = _compute_article_grid_in_rotated_inner(sm, ib)

    # 2-column when inner IS the sole article (single article per inner box)
    two_col = (n_arts == 1)

    if two_col:
        col_master_w = usable_w * 0.58
        col_inner_w  = usable_w * 0.42
        max_img_h    = content_h * 0.62

        img3d_w, img3d_h = _scale_image(png_master, col_master_w - 0.2*rl_cm, max_img_h)
        img_in_w, img_in_h = _scale_image(png_inner, col_inner_w - 0.2*rl_cm, max_img_h)

        master_rows = [
            _kv_row("Contenedor",       container_name,                            col_master_w, styles),
            _kv_row("Dimensiones ext.", f"{L_e:.1f} × {W_e:.1f} × {H_e:.1f} cm", col_master_w, styles),
            _kv_row("Peso bruto",       f"{total_weight:.2f} kg",                  col_master_w, styles),
            _kv_row("Cuadrícula L×A×H", f"{nL_m} × {nW_m} × {nH_m}",             col_master_w, styles),
            _kv_row("Cajas interiores", str(inners_used),                          col_master_w, styles),
        ]
        inner_rows = [
            _kv_row("Dimensiones ext.", f"{Lr:.1f} × {Wr:.1f} × {Hr:.1f} cm",    col_inner_w, styles),
            _kv_row("Peso artículo",    f"{a_kg:.3f} kg",                          col_inner_w, styles),
            _kv_row("Tamaño de lote",   str(lot_size),                             col_inner_w, styles),
        ]

        combined = Table(
            [
                [Paragraph("CONTENEDOR",   styles["graph_title"]),
                 Paragraph("CAJA INTERIOR", styles["graph_title"])],
                [RLImage(io.BytesIO(png_master), width=img3d_w, height=img3d_h),
                 RLImage(io.BytesIO(png_inner),  width=img_in_w, height=img_in_h)],
                [_data_block(master_rows, col_master_w),
                 _data_block(inner_rows,  col_inner_w)],
            ],
            colWidths=[col_master_w, col_inner_w],
        )
        combined.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN",  (0, 0), (-1,  0), "LEFT"),
            ("LEFTPADDING",   (0, 0), (-1,  0), lpad),
            ("ALIGN",  (0, 1), (-1,  1), "CENTER"),
            ("VALIGN", (0, 1), (-1,  1), "MIDDLE"),
            ("LEFTPADDING",   (0, 1), (-1,  1), 0),
            ("ALIGN",  (0, 2), (-1,  2), "LEFT"),
            ("LEFTPADDING",   (0, 2), (-1,  2), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1,  0), 4),
            ("BOTTOMPADDING", (0, 1), (-1,  1), 8),
            ("BOTTOMPADDING", (0, 2), (-1,  2), 0),
            ("LINEAFTER", (0, 0), (0, -1), 0.5, _GREYE0),
        ]))
        n_rows     = max(len(master_rows), len(inner_rows))
        combined_h = max(img3d_h, img_in_h) + 8 + n_rows * 20 + 12

    else:
        # 3-column: Contenedor | Caja Interior | Artículo
        col_master_w = usable_w * 0.40
        col_inner_w  = usable_w * 0.33
        col_art_w    = usable_w * 0.27
        max_img_h    = content_h * 0.60

        img3d_w, img3d_h   = _scale_image(png_master,  col_master_w - 0.2*rl_cm, max_img_h)
        img_in_w, img_in_h = _scale_image(png_inner,   col_inner_w  - 0.2*rl_cm, max_img_h)
        art_src = png_article if png_article else png_inner
        img_ar_w, img_ar_h = _scale_image(art_src, col_art_w - 0.2*rl_cm, max_img_h)

        master_rows = [
            _kv_row("Contenedor",       container_name,                            col_master_w, styles),
            _kv_row("Dimensiones ext.", f"{L_e:.1f} × {W_e:.1f} × {H_e:.1f} cm", col_master_w, styles),
            _kv_row("Peso bruto",       f"{total_weight:.2f} kg",                  col_master_w, styles),
            _kv_row("Cuadrícula L×A×H", f"{nL_m} × {nW_m} × {nH_m}",             col_master_w, styles),
            _kv_row("Cajas interiores", str(inners_used),                          col_master_w, styles),
        ]
        inner_rows = [
            _kv_row("Dimensiones ext.", f"{Lr:.1f} × {Wr:.1f} × {Hr:.1f} cm",    col_inner_w, styles),
            _kv_row("Peso bruto",       f"{inner_w_kg:.2f} kg",                   col_inner_w, styles),
            _kv_row("Arts. por caja",   str(n_arts),                               col_inner_w, styles),
            _kv_row("Cuadrícula art.",  f"{nL_r} × {nW_r} × {nH_r}",             col_inner_w, styles),
        ]
        art_rows = [
            _kv_row("Dimensiones",      f"{a_L:.1f} × {a_W:.1f} × {a_H:.1f} cm", col_art_w, styles),
            _kv_row("Peso unitario",    f"{a_kg:.3f} kg",                          col_art_w, styles),
            _kv_row("Tamaño de lote",   str(lot_size),                             col_art_w, styles),
        ]

        combined = Table(
            [
                [Paragraph("CONTENEDOR",   styles["graph_title"]),
                 Paragraph("CAJA INTERIOR", styles["graph_title"]),
                 Paragraph("ARTÍCULO",      styles["graph_title"])],
                [RLImage(io.BytesIO(png_master), width=img3d_w, height=img3d_h),
                 RLImage(io.BytesIO(png_inner),  width=img_in_w, height=img_in_h),
                 RLImage(io.BytesIO(art_src),    width=img_ar_w, height=img_ar_h)],
                [_data_block(master_rows, col_master_w),
                 _data_block(inner_rows,  col_inner_w),
                 _data_block(art_rows,    col_art_w)],
            ],
            colWidths=[col_master_w, col_inner_w, col_art_w],
        )
        combined.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN",  (0, 0), (-1,  0), "LEFT"),
            ("LEFTPADDING",   (0, 0), (-1,  0), lpad),
            ("ALIGN",  (0, 1), (-1,  1), "CENTER"),
            ("VALIGN", (0, 1), (-1,  1), "MIDDLE"),
            ("LEFTPADDING",   (0, 1), (-1,  1), 0),
            ("ALIGN",  (0, 2), (-1,  2), "LEFT"),
            ("LEFTPADDING",   (0, 2), (-1,  2), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1,  0), 4),
            ("BOTTOMPADDING", (0, 1), (-1,  1), 8),
            ("BOTTOMPADDING", (0, 2), (-1,  2), 0),
            ("LINEAFTER", (0, 0), (0, -1), 0.5, _GREYE0),
            ("LINEAFTER", (1, 0), (1, -1), 0.5, _GREYE0),
        ]))
        n_rows     = max(len(master_rows), len(inner_rows), len(art_rows))
        combined_h = max(img3d_h, img_in_h, img_ar_h) + 8 + n_rows * 20 + 12

    pad = max(0.0, (content_h - combined_h) / 2)
    return [Spacer(1, pad), combined, Spacer(1, pad)]


# ── Punto de entrada público ──────────────────────────────────────────────────

def build_pdf_b64(
    fig: go.Figure,
    doc: dict,
    product_meta: Optional[dict] = None,
    title: str = "Packaging Proposal",
) -> Optional[str]:
    """
    Genera el PDF apaisado A4 y lo devuelve como string base64.
    Retorna None si ocurre cualquier error.
    """
    try:
        styles = _build_styles()

        page_w, page_h = rl_landscape(A4)
        margin_h = 1.8 * rl_cm
        margin_v = 1.6 * rl_cm
        disc_res = _DISCLAIMER_RESERVED_CM * rl_cm
        usable_w = page_w - 2 * margin_h
        bottom_m = margin_v + disc_res
        story_h  = page_h - margin_v - bottom_m
        content_h = story_h - _HEADER_H_PT

        sm  = doc.get("selected_master") or {}
        ib  = doc.get("inner_box") or {}
        ad  = doc.get("article_dims") or {}

        ext_dims_raw   = sm.get("ext_dims") or [1.0, 1.0, 1.0]
        inner_dims_raw = sm.get("inner_dims_rotated") or [1.0, 1.0, 1.0]
        ext_dims = tuple((list(ext_dims_raw)   + [1.0, 1.0, 1.0])[:3])
        Lr, Wr, Hr = (list(inner_dims_raw) + [1.0, 1.0, 1.0])[:3]

        nL_r, nW_r, nH_r, art_L, art_W, art_H, wall = _compute_article_grid_in_rotated_inner(sm, ib)

        png_master  = render_master_png(fig, ext_dims)
        png_inner   = render_inner_with_articles_png(
            Lr, Wr, Hr, nL_r, nW_r, nH_r, art_L, art_W, art_H, wall
        )
        a_L = ad.get("length_cm", art_L)
        a_W = ad.get("width_cm",  art_W)
        a_H = ad.get("height_cm", art_H)
        png_article = render_article_png(a_L, a_W, a_H)

        def _page_number(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 6.5)
            canvas.setFillColor(_GREYCC)
            canvas.drawRightString(page_w - margin_h, margin_v - 10, f"Pág. {_doc.page}")
            canvas.restoreState()

        def _first_page(canvas, _doc):
            _page_number(canvas, _doc)


        story = _build_header(title, styles, product_meta) + _build_content_block(
            png_master, png_inner, png_article, doc, usable_w, content_h, styles
        )

        pdf_buf = io.BytesIO()
        rl_doc = SimpleDocTemplate(
            pdf_buf,
            pagesize=rl_landscape(A4),
            rightMargin=margin_h,
            leftMargin=margin_h,
            topMargin=margin_v,
            bottomMargin=bottom_m,
        )
        rl_doc.build(story, onFirstPage=_first_page, onLaterPages=_page_number)
        pdf_buf.seek(0)
        return base64.b64encode(pdf_buf.read()).decode("utf-8")

    except Exception:
        log.exception("Error generando PDF para propuesta %s", doc.get("id", "?"))
        return None
