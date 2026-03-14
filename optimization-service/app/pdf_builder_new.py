"""
Genera el PDF de propuesta de packaging en base64.

Layout:
  - Cabecera: "PACKAGING PROPOSAL" + nombre producto / talla / EAN
  - 1 columna cuando es directo (inner == artículo, grid 1×1×1)
  - 3 columnas: CONTENEDOR | CAJA INTERIOR (con artículos) | ARTÍCULO
"""

from __future__ import annotations

import base64
import io
import logging
import re
from typing import List, Optional, Tuple

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
_BLACK  = rl_colors.HexColor("#000000")
_GREY33 = rl_colors.HexColor("#333333")
_GREY66 = rl_colors.HexColor("#666666")
_GREYCC = rl_colors.HexColor("#CCCCCC")
_GREYE0 = rl_colors.HexColor("#E0E0E0")

_DISCLAIMER = (
    "This packaging proposal is generated based on the inner information "
    "provided by supplier, make sure this information is correct. "
    "This solution not only follows all the mandatory points established in the "
    "Logistics Normative, it also adds additional requirements and insights "
    "of all the supply chain areas. "
    "Follow this proposal is mandatory and will be verified at our warehouse. "
    "Any non-compliance in dimensions, weight and/or units may result "
    "in penalties for the incurred extra cost damages. "
    "If during final packing production, master box dimensions exceed a tolerance "
    "of +/-1 cm or you find any technical - product related "
    "limitations that do not allow you to follow the proposal, please contact "
    "your packaging coordinator."
)

_HEADER_H_PT = 58          # measured empirically — increases when product info present
_DISCLAIMER_RESERVED_CM = 0.3


# ── Geometry helper ───────────────────────────────────────────────────────────

def _box_verts(x, y, z, dx, dy, dz):
    """Return 6 quad-face polygons for a box, suitable for Poly3DCollection."""
    x1, y1, z1 = x + dx, y + dy, z + dz
    return [
        [(x, y, z), (x1, y, z), (x1, y1, z),  (x, y1, z)],    # bottom
        [(x, y, z1),(x1, y, z1),(x1, y1, z1), (x, y1, z1)],   # top
        [(x, y, z), (x1, y, z), (x1, y,  z1), (x, y,  z1)],   # front
        [(x, y1, z),(x1, y1, z),(x1, y1, z1), (x, y1, z1)],   # back
        [(x, y, z), (x, y1, z), (x,  y1, z1), (x, y,  z1)],   # left
        [(x1, y, z),(x1, y1, z),(x1, y1, z1), (x1, y,  z1)],  # right
    ]


# ── Estilos ───────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    return dict(
        title=ParagraphStyle("ptitle", fontName="Helvetica-Bold", fontSize=10,
                             leading=14, textColor=_BLACK, alignment=TA_LEFT,
                             charSpace=1, spaceAfter=0),
        subtitle=ParagraphStyle("psub", fontName="Helvetica", fontSize=8,
                                leading=11, textColor=_GREY66, alignment=TA_LEFT),
        product_info=ParagraphStyle("pprod", fontName="Helvetica", fontSize=8,
                                    leading=11, textColor=_GREY33, alignment=TA_LEFT),
        graph_title=ParagraphStyle("pgtitle", fontName="Helvetica-Bold", fontSize=8,
                                   leading=11, textColor=_GREY33, alignment=TA_CENTER),
        info_label=ParagraphStyle("pilbl", fontName="Helvetica", fontSize=7,
                                  leading=10, textColor=_GREY66, alignment=TA_LEFT),
        info_value=ParagraphStyle("pival", fontName="Helvetica", fontSize=7,
                                  leading=10, textColor=_GREY33, alignment=TA_LEFT),
    )


# ── Matplotlib helpers ────────────────────────────────────────────────────────

def _parse_color(c, default_rgb=(0.5, 0.5, 0.5), default_alpha=0.3):
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


def _clean_ax3d(ax):
    ax.set_axis_off()
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("none")
    ax.grid(False)


def _dim_annotation(ax, p1, p2, label, color="#7a7a7a", fontsize=8.0, offset=(0, 0, 0)):
    x1, y1, z1 = p1[0] + offset[0], p1[1] + offset[1], p1[2] + offset[2]
    x2, y2, z2 = p2[0] + offset[0], p2[1] + offset[1], p2[2] + offset[2]
    ax.plot([x1, x2], [y1, y2], [z1, z2], color=color, linewidth=0.9, zorder=10)
    ax.scatter([x1, x2], [y1, y2], [z1, z2], color=color, s=8, marker="|",
               zorder=11, linewidths=1.0)
    for (ox, oy, oz), (cx, cy, cz) in [(p1, (x1, y1, z1)), (p2, (x2, y2, z2))]:
        ax.plot([ox, cx], [oy, cy], [oz, cz], color=color, linewidth=0.5,
                linestyle="--", zorder=9, alpha=0.5)
    mx, my, mz = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2
    ax.text(mx, my, mz, label, ha="center", va="center", fontsize=fontsize,
            color="#111111", fontfamily="DejaVu Sans", zorder=12,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor="none", alpha=0.9))


_AIR_KEYWORDS = ("air", "void", "aire")


# ── PNG renders ───────────────────────────────────────────────────────────────

def render_master_png(fig: go.Figure,
                      ext_dims: Tuple[float, float, float],
                      dpi: int = 130) -> bytes:
    """Matplotlib 3-D render of the master container from a Plotly figure."""
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
                alpha=opacity, facecolor=(r, g, b),
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
            seg_x, seg_y, seg_z = [], [], []
            for xi, yi, zi in zip(x_raw, y_raw, z_raw):
                if xi is None or yi is None or zi is None:
                    if len(seg_x) >= 2:
                        ax.plot(seg_x, seg_y, seg_z, color=(r, g, b),
                                linewidth=0.6, alpha=0.1 if is_air else 0.85)
                    seg_x, seg_y, seg_z = [], [], []
                else:
                    seg_x.append(float(xi))
                    seg_y.append(float(yi))
                    seg_z.append(float(zi))
            if len(seg_x) >= 2:
                ax.plot(seg_x, seg_y, seg_z, color=(r, g, b),
                        linewidth=0.6, alpha=0.1 if is_air else 0.85)

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

        _dim_annotation(ax, (xmax, ymin, zmin), (xmax, ymin, zmax),
                        f"H  {H_ext:.1f} cm",
                        offset=(gap_x * 1.5, -gap_y * 0.3, 0), fontsize=fs)
        _dim_annotation(ax, (xmax, ymin, zmin), (xmax, ymax, zmin),
                        f"W  {W_ext:.1f} cm",
                        offset=(gap_x * 1.5, gap_y * 0.3, -gap_z * 0.5), fontsize=fs)
        _dim_annotation(ax, (xmin, ymax, zmin), (xmax, ymax, zmin),
                        f"L  {L_ext:.1f} cm",
                        offset=(0, gap_y * 1.5, -gap_z * 0.5), fontsize=fs)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def render_inner_png(Lr: float, Wr: float, Hr: float,
                     inner_axes_used: Optional[List[str]] = None,
                     inner_grid: Optional[List[int]] = None,
                     wall_cm: float = 0.3,
                     dpi: int = 130) -> bytes:
    """
    Render 3-D inner box (blue) with article boxes packed inside (yellow).

    inner_axes_used: e.g. ["med","min","max"] — which inner axis occupies L/W/H in this render
    inner_grid:      [nMax, nMed, nMin] from inner_box.grid
    wall_cm:         wall thickness per side in cm
    """
    _FILL = (0x4D / 255, 0xA3 / 255, 0xFF / 255)   # #4da3ff
    _EDGE = (0x1A / 255, 0x73 / 255, 0xE8 / 255)   # #1a73e8
    _OPA  = 0.25
    _ART_FILL = (0xF5 / 255, 0xC5 / 255, 0x18 / 255)  # #f5c518
    _ART_EDGE = (0xC8 / 255, 0xA0 / 255, 0x00 / 255)  # #c8a000
    _ART_OPA  = 0.55

    mpl_fig = plt.figure(figsize=(6.0, 6.0), dpi=dpi)
    ax = mpl_fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    mpl_fig.patch.set_facecolor("white")
    _clean_ax3d(ax)

    # Draw inner box
    poly = Poly3DCollection(_box_verts(0, 0, 0, Lr, Wr, Hr),
                            alpha=_OPA, facecolor=_FILL, edgecolor=_EDGE, linewidth=0.8)
    ax.add_collection3d(poly)

    # Draw article boxes inside
    if inner_axes_used and inner_grid and len(inner_axes_used) == 3 and len(inner_grid) == 3:
        _ax_idx = {"max": 0, "med": 1, "min": 2}
        nL = inner_grid[_ax_idx.get(inner_axes_used[0], 0)]
        nW = inner_grid[_ax_idx.get(inner_axes_used[1], 1)]
        nH = inner_grid[_ax_idx.get(inner_axes_used[2], 2)]
        int_L = Lr - 2 * wall_cm
        int_W = Wr - 2 * wall_cm
        int_H = Hr - 2 * wall_cm
        if nL > 0 and nW > 0 and nH > 0 and int_L > 0.1 and int_W > 0.1 and int_H > 0.1:
            aL = int_L / nL
            aW = int_W / nW
            aH = int_H / nH
            for iL in range(nL):
                for iW in range(nW):
                    for iH in range(nH):
                        x0 = wall_cm + iL * aL
                        y0 = wall_cm + iW * aW
                        z0 = wall_cm + iH * aH
                        a = Poly3DCollection(
                            _box_verts(x0, y0, z0, aL, aW, aH),
                            alpha=_ART_OPA, facecolor=_ART_FILL,
                            edgecolor=_ART_EDGE, linewidth=0.4,
                        )
                        ax.add_collection3d(a)

    ax.set_xlim(-0.05 * Lr, Lr * 1.35)
    ax.set_ylim(-0.05 * Wr, Wr * 1.35)
    ax.set_zlim(0, Hr * 1.2)
    ax.set_box_aspect([Lr, Wr, Hr])

    gap_x, gap_y, gap_z = Lr * 0.08, Wr * 0.08, Hr * 0.08
    fs = 8.0
    _dim_annotation(ax, (Lr, 0, 0), (Lr, 0, Hr), f"H  {Hr:.1f} cm",
                    offset=(gap_x * 1.5, -gap_y * 0.3, 0), fontsize=fs)
    _dim_annotation(ax, (Lr, 0, 0), (Lr, Wr, 0), f"W  {Wr:.1f} cm",
                    offset=(gap_x * 1.5, gap_y * 0.3, -gap_z * 0.5), fontsize=fs)
    _dim_annotation(ax, (0, Wr, 0), (Lr, Wr, 0), f"L  {Lr:.1f} cm",
                    offset=(0, gap_y * 1.5, -gap_z * 0.5), fontsize=fs)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def render_article_png(length_cm: float, width_cm: float, height_cm: float,
                       dpi: int = 130) -> bytes:
    """Render a standalone article box in yellow/gold."""
    _FILL = (0xF5 / 255, 0xC5 / 255, 0x18 / 255)   # #f5c518
    _EDGE = (0xC8 / 255, 0xA0 / 255, 0x00 / 255)   # #c8a000
    _OPA  = 0.55

    L, W, H = max(length_cm, 0.1), max(width_cm, 0.1), max(height_cm, 0.1)

    mpl_fig = plt.figure(figsize=(6.0, 6.0), dpi=dpi)
    ax = mpl_fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    mpl_fig.patch.set_facecolor("white")
    _clean_ax3d(ax)

    poly = Poly3DCollection(_box_verts(0, 0, 0, L, W, H),
                            alpha=_OPA, facecolor=_FILL, edgecolor=_EDGE, linewidth=0.8)
    ax.add_collection3d(poly)

    ax.set_xlim(-0.05 * L, L * 1.35)
    ax.set_ylim(-0.05 * W, W * 1.35)
    ax.set_zlim(0, H * 1.2)
    ax.set_box_aspect([L, W, H])

    gap_x, gap_y, gap_z = L * 0.08, W * 0.08, H * 0.08
    fs = 8.0
    _dim_annotation(ax, (L, 0, 0), (L, 0, H), f"H  {H:.1f} cm",
                    offset=(gap_x * 1.5, -gap_y * 0.3, 0), fontsize=fs)
    _dim_annotation(ax, (L, 0, 0), (L, W, 0), f"W  {W:.1f} cm",
                    offset=(gap_x * 1.5, gap_y * 0.3, -gap_z * 0.5), fontsize=fs)
    _dim_annotation(ax, (0, W, 0), (L, W, 0), f"L  {L:.1f} cm",
                    offset=(0, gap_y * 1.5, -gap_z * 0.5), fontsize=fs)

    ax.view_init(elev=25, azim=35)
    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


# ── ReportLab layout ──────────────────────────────────────────────────────────

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
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _data_block(rows: list, col_w: float) -> Table:
    lpad = int(0.35 * rl_cm)
    t = Table([[r] for r in rows], colWidths=[col_w - 0.4 * rl_cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), lpad),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _build_header(styles: dict, product_meta: Optional[dict] = None) -> list:
    flowables = [
        Paragraph("PACKAGING PROPOSAL", styles["title"]),
        Spacer(1, 0.05 * rl_cm),
        Paragraph("Packaging Optimization Report", styles["subtitle"]),
    ]
    if product_meta:
        parts = []
        if product_meta.get("product_name"):
            parts.append(product_meta["product_name"])
        if product_meta.get("size_name"):
            parts.append(f"Talla: {product_meta['size_name']}")
        if product_meta.get("ean_code"):
            parts.append(f"EAN: {product_meta['ean_code']}")
        if parts:
            flowables.append(Spacer(1, 0.05 * rl_cm))
            flowables.append(Paragraph("  ·  ".join(parts), styles["product_info"]))
    flowables += [
        Spacer(1, 0.15 * rl_cm),
        HRFlowable(width="100%", thickness=0.5, color=_GREYCC, spaceAfter=0, spaceBefore=0),
        Spacer(1, 0.2 * rl_cm),
    ]
    return flowables


def _build_content_block(png_master: bytes, png_inner: bytes, png_article: bytes,
                         doc: dict, usable_w: float, content_h: float,
                         styles: dict) -> list:
    lpad = int(0.35 * rl_cm)
    max_img_h = content_h * 0.62

    sm          = doc.get("selected_master") or {}
    grid        = sm.get("grid") or [1, 1, 1]
    inners_used = sm.get("inners_used", 1)
    ext_dims    = sm.get("ext_dims") or [0, 0, 0]
    inner_dims  = sm.get("inner_dims_rotated") or [0, 0, 0]
    nL, nW, nH  = (grid + [1, 1, 1])[:3]
    L_e, W_e, H_e = (list(ext_dims) + [0, 0, 0])[:3]
    Lr, Wr, Hr    = (list(inner_dims) + [0, 0, 0])[:3]

    total_weight  = sm.get("total_weight_kg", 0)
    inner_w_kg    = total_weight / inners_used if inners_used else 0.0
    container_name = sm.get("container_name", "—")
    lot_size      = doc.get("lot_size", "—")

    art   = doc.get("article_dims") or {}
    art_l = art.get("length_cm", 0)
    art_w = art.get("width_cm", 0)
    art_h = art.get("height_cm", 0)
    art_kg = art.get("weight_kg", 0)

    is_direct = inners_used == 1 and tuple(grid[:3]) == (1, 1, 1)

    if is_direct:
        # ── Single column: CAJA INTERIOR ─────────────────────────────────────
        img_w, img_h = _scale_image(png_inner,
                                    max_w=usable_w - 0.2 * rl_cm,
                                    max_h=max_img_h)
        rows = [
            _kv_row("Dimensions (ext)", f"{Lr:.1f} × {Wr:.1f} × {Hr:.1f} cm", usable_w, styles),
            _kv_row("Gross weight",     f"{total_weight:.2f} kg",              usable_w, styles),
        ]
        combined = Table(
            [
                [Paragraph("CAJA INTERIOR", styles["graph_title"])],
                [RLImage(io.BytesIO(png_inner), width=img_w, height=img_h)],
                [_data_block(rows, usable_w)],
            ],
            colWidths=[usable_w],
        )
        combined.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("ALIGN",         (0, 1), (0,  1),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), lpad),
            ("LEFTPADDING",   (0, 1), (0,  1),  0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (0,  1),  8),
        ]))
        combined_h = img_h + 8 + 2 * 20 + 12

    else:
        # ── Three columns: CONTENEDOR | CAJA INTERIOR | ARTÍCULO ─────────────
        col_master_w  = usable_w * 0.42
        col_inner_w   = usable_w * 0.33
        col_article_w = usable_w * 0.25

        img_m_w, img_m_h = _scale_image(png_master,
                                        max_w=col_master_w  - 0.2 * rl_cm, max_h=max_img_h)
        img_i_w, img_i_h = _scale_image(png_inner,
                                        max_w=col_inner_w   - 0.2 * rl_cm, max_h=max_img_h)
        img_a_w, img_a_h = _scale_image(png_article,
                                        max_w=col_article_w - 0.2 * rl_cm, max_h=max_img_h)

        master_rows = [
            _kv_row("Container",        container_name,                           col_master_w, styles),
            _kv_row("Dimensions (ext)", f"{L_e:.1f} × {W_e:.1f} × {H_e:.1f} cm", col_master_w, styles),
            _kv_row("Gross weight",     f"{total_weight:.2f} kg",                 col_master_w, styles),
            _kv_row("Grid (L×W×H)",     f"{nL} × {nW} × {nH}",                   col_master_w, styles),
        ]
        inner_rows = [
            _kv_row("Dimensions (ext)", f"{Lr:.1f} × {Wr:.1f} × {Hr:.1f} cm", col_inner_w, styles),
            _kv_row("Gross weight",     f"{inner_w_kg:.2f} kg",                col_inner_w, styles),
            _kv_row("Inner per master", str(inners_used),                      col_inner_w, styles),
        ]
        article_rows = [
            _kv_row("Dimensions",  f"{art_l:.1f} × {art_w:.1f} × {art_h:.1f} cm", col_article_w, styles),
            _kv_row("Weight",      f"{art_kg:.3f} kg",                              col_article_w, styles),
            _kv_row("Lot size",    str(lot_size),                                   col_article_w, styles),
        ]

        combined = Table(
            [
                [Paragraph("CONTENEDOR",   styles["graph_title"]),
                 Paragraph("CAJA INTERIOR", styles["graph_title"]),
                 Paragraph("ARTÍCULO",      styles["graph_title"])],
                [RLImage(io.BytesIO(png_master),  width=img_m_w, height=img_m_h),
                 RLImage(io.BytesIO(png_inner),   width=img_i_w, height=img_i_h),
                 RLImage(io.BytesIO(png_article),  width=img_a_w, height=img_a_h)],
                [_data_block(master_rows,  col_master_w),
                 _data_block(inner_rows,   col_inner_w),
                 _data_block(article_rows, col_article_w)],
            ],
            colWidths=[col_master_w, col_inner_w, col_article_w],
        )
        combined.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("ALIGN",         (0, 0), (-1, 0),  "LEFT"),
            ("LEFTPADDING",   (0, 0), (-1, 0),  lpad),
            ("ALIGN",         (0, 1), (-1, 1),  "CENTER"),
            ("LEFTPADDING",   (0, 1), (-1, 1),  0),
            ("ALIGN",         (0, 2), (-1, 2),  "LEFT"),
            ("LEFTPADDING",   (0, 2), (-1, 2),  0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  4),
            ("BOTTOMPADDING", (0, 1), (-1, 1),  8),
            ("BOTTOMPADDING", (0, 2), (-1, 2),  0),
            ("LINEAFTER",     (0, 0), (1,  -1), 0.5, _GREYE0),
        ]))
        combined_h = max(img_m_h, img_i_h, img_a_h) + 8 + 4 * 20 + 12

    pad = max(0.0, (content_h - combined_h) / 2)
    return [Spacer(1, pad), combined, Spacer(1, pad)]


# ── Public entry point ────────────────────────────────────────────────────────

def build_pdf_b64(fig: go.Figure,
                  doc: dict,
                  product_meta: Optional[dict] = None) -> Optional[str]:
    """
    Genera el PDF apaisado A4 y lo devuelve como string base64.
    Retorna None si ocurre cualquier error.

    Args:
        fig:          figura Plotly ya construida por _build_proposal_figure
        doc:          documento de propuesta (dict de MongoDB)
        product_meta: dict con product_name, size_name, ean_code (opcional)
    """
    try:
        styles = _build_styles()

        page_w, page_h = rl_landscape(A4)
        margin_h  = 1.8 * rl_cm
        margin_v  = 1.6 * rl_cm
        disc_res  = _DISCLAIMER_RESERVED_CM * rl_cm
        usable_w  = page_w - 2 * margin_h
        bottom_m  = margin_v + disc_res
        story_h   = page_h - margin_v - bottom_m
        content_h = story_h - _HEADER_H_PT

        sm             = doc.get("selected_master") or {}
        ext_dims_raw   = sm.get("ext_dims") or [1.0, 1.0, 1.0]
        inner_dims_raw = sm.get("inner_dims_rotated") or [1.0, 1.0, 1.0]
        inner_axes     = sm.get("inner_axes_used")                 # e.g. ["med","min","max"]
        ext_dims       = tuple((list(ext_dims_raw) + [1.0, 1.0, 1.0])[:3])
        Lr, Wr, Hr     = (list(inner_dims_raw) + [1.0, 1.0, 1.0])[:3]

        ib      = doc.get("inner_box") or {}
        ig_raw  = ib.get("grid")                                    # [nMax, nMed, nMin]
        wall_cm = ib.get("wall_thickness_mm", 3.0) / 10.0          # per side

        art   = doc.get("article_dims") or {}
        art_l = art.get("length_cm", 1.0)
        art_w = art.get("width_cm",  1.0)
        art_h = art.get("height_cm", 1.0)

        # Generate all three PNGs
        png_master  = render_master_png(fig, ext_dims)
        png_inner   = render_inner_png(Lr, Wr, Hr,
                                       inner_axes_used=inner_axes,
                                       inner_grid=ig_raw,
                                       wall_cm=wall_cm)
        png_article = render_article_png(art_l, art_w, art_h)

        def _page_number(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 6.5)
            canvas.setFillColor(_GREYCC)
            canvas.drawRightString(page_w - margin_h, margin_v - 10,
                                   f"Page {_doc.page}")
            canvas.restoreState()

        def _first_page(canvas, _doc):
            _page_number(canvas, _doc)
            canvas.saveState()
            _ds = ParagraphStyle("_disc", fontName="Helvetica-Oblique", fontSize=6,
                                 leading=8, textColor=_GREY66, alignment=TA_LEFT)
            from reportlab.platypus import Paragraph as _Para
            _p = _Para(_DISCLAIMER, _ds)
            _p.wrap(usable_w, 40)
            _p.drawOn(canvas, margin_h, margin_v - 14)
            canvas.restoreState()

        story = _build_header(styles, product_meta) + _build_content_block(
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
