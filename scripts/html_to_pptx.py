# -*- coding: utf-8 -*-
"""Chuyển slides/bao_cao_cuoi_ky.html thành file PowerPoint sửa được.

Cách làm: mở HTML bằng Chromium (Playwright), đo vị trí từng khối trên trang 1920x1080,
rồi vẽ lại bằng hình, bảng và biểu đồ gốc của PowerPoint (không chụp ảnh màn hình).
Quy đổi: 1 px trên trang = 6350 EMU = 0,5 pt.

Cần: pip install python-pptx playwright (Chromium: python -m playwright install chromium)
Chạy: python scripts/html_to_pptx.py
"""
import re
import sys
from pathlib import Path

from lxml import etree
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "slides" / "bao_cao_cuoi_ky.html"
OUT = ROOT / "slides" / "bao_cao_cuoi_ky.pptx"

PX = 6350  # 1 px của trang 1920x1080 tính ra EMU
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
SECTIONS = ["Giới thiệu", "Bài toán", "Cơ sở lý thuyết", "Nghiên cứu nền tảng", "Phương pháp", "Hệ thống", "Kết quả", "Kết luận"]

# Người nhận có thể không cài Be Vietnam Pro, nên đo và xuất bằng font có sẵn trong Office.
FONT_OVERRIDE = """
:root { --sans: Arial, sans-serif !important; --mono: Consolas, monospace !important; }
#stage, #stage * { text-rendering: geometricPrecision; }
svg, svg * { font-family: Arial, sans-serif !important; }
.cover h1 { font-size: 80px !important; }  /* Arial đậm rộng hơn: giữ tiêu đề bìa trên một dòng */
"""

# Đoạn JS chạy trong trang: duyệt DOM của một slide, trả về danh sách phần tử để vẽ theo đúng thứ tự.
EXTRACT_JS = r"""
(index) => {
  const slide = document.querySelectorAll('.slide')[index];
  const items = [];
  const hex = c => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(s => parseFloat(s));
    if (p.length === 4 && p[3] === 0) return null;
    return p.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  const box = r => ({ x: r.left, y: r.top, w: r.width, h: r.height });
  const isInline = el => el.tagName === 'BR' || ['inline', 'inline-block'].includes(getComputedStyle(el).display);
  const onlyInline = el => [...el.children].every(isInline);
  const textRect = el => { const r = document.createRange(); r.selectNodeContents(el); return r.getBoundingClientRect(); };

  // Tách chữ trong một khối thành các run có định dạng riêng
  function runsOf(block) {
    const runs = [];
    const pre = getComputedStyle(block).whiteSpace === 'pre';
    (function walk(node) {
      for (const ch of node.childNodes) {
        if (ch.nodeType === 3) {
          let t = ch.textContent;
          if (!pre) t = t.replace(/[ \t\r\n]+/g, ' ');
          if (!t) continue;
          const el = ch.parentElement, cs = getComputedStyle(el);
          let hl = null;
          for (let e = el; e && e !== block; e = e.parentElement) {
            hl = hex(getComputedStyle(e).backgroundColor);
            if (hl) break;
          }
          runs.push({ t, size: parseFloat(cs.fontSize), bold: parseInt(cs.fontWeight) >= 600, italic: cs.fontStyle === 'italic',
                      mono: /Consolas/.test(cs.fontFamily), color: hex(cs.color), hl, tag: !!el.closest('.tag') });
        } else if (ch.nodeType === 1) {
          if (ch.tagName === 'BR') runs.push({ br: true });
          else walk(ch);
        }
      }
    })(block);
    if (!pre) {
      for (let i = 0; i < runs.length; i++) {
        const atStart = i === 0 || runs[i - 1].br, atEnd = i === runs.length - 1 || runs[i + 1].br;
        if (runs[i].br) continue;
        if (atStart) runs[i].t = runs[i].t.replace(/^ +/, '');
        if (atEnd) runs[i].t = runs[i].t.replace(/ +$/, '');
      }
    }
    return runs.filter(r => r.br || r.t);
  }

  function para(block, extra) {
    const cs = getComputedStyle(block);
    return Object.assign({ algn: cs.textAlign, lh: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.3, runs: runsOf(block) }, extra || {});
  }

  function emitText(el, paras, fillHex, role) {
    const cs = getComputedStyle(el), b = el.getBoundingClientRect(), t = textRect(el);
    items.push(Object.assign({ type: 'text', paras, fill: fillHex, role: role || null, pre: cs.whiteSpace === 'pre',
      padL: parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth), padR: parseFloat(cs.paddingRight) + parseFloat(cs.borderRightWidth),
      gapT: t.top - b.top, gapB: b.bottom - t.bottom }, box(b)));
  }

  function emitBorders(el) {
    const cs = getComputedStyle(el), b = el.getBoundingClientRect();
    const L = parseFloat(cs.borderLeftWidth), T = parseFloat(cs.borderTopWidth), B = parseFloat(cs.borderBottomWidth);
    if (L > 0 && hex(cs.borderLeftColor)) items.push({ type: 'rect', x: b.left, y: b.top, w: L, h: b.height, fill: hex(cs.borderLeftColor) });
    if (T > 0 && hex(cs.borderTopColor)) items.push({ type: 'rect', x: b.left, y: b.top, w: b.width, h: T, fill: hex(cs.borderTopColor) });
    if (B > 0 && hex(cs.borderBottomColor)) items.push({ type: 'rect', x: b.left, y: b.bottom - B, w: b.width, h: B, fill: hex(cs.borderBottomColor) });
  }

  function emitTable(tb) {
    const rows = [...tb.rows].map(tr => ({
      h: tr.getBoundingClientRect().height,
      cells: [...tr.cells].map(td => {
        const cs = getComputedStyle(td);
        return { w: td.getBoundingClientRect().width, fill: hex(cs.backgroundColor), align: cs.textAlign, valign: cs.verticalAlign,
          padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight), padT: parseFloat(cs.paddingTop), padB: parseFloat(cs.paddingBottom),
          rule: parseFloat(cs.borderBottomWidth) > 0 ? hex(cs.borderBottomColor) : null, para: para(td) };
      })
    }));
    items.push(Object.assign({ type: 'table', rows }, box(tb.getBoundingClientRect())));
  }

  function emitList(ul) {
    const gap = parseFloat(getComputedStyle(ul).rowGap) || 0;
    const paras = [...ul.children].map((li, i) => para(li, { bullet: true, marL: parseFloat(getComputedStyle(li).paddingLeft), before: i ? gap : 0 }));
    emitText(ul, paras, hex(getComputedStyle(ul).backgroundColor));
  }

  // Sơ đồ SVG: chữ nằm trong hình chữ nhật thì gộp vào hình đó để di chuyển cùng nhau
  function emitSvg(svg) {
    const m = svg.getScreenCTM();
    const pt = (x, y) => [m.a * x + m.e, m.d * y + m.f];
    for (const p of svg.querySelectorAll('path')) {
      const tokens = p.getAttribute('d').match(/[MHVLz]|-?[\d.]+/g);
      const pts = []; let i = 0, x = 0, y = 0, closed = false;
      while (i < tokens.length) {
        const c = tokens[i++];
        if (c === 'z') { closed = true; continue; }
        if (c === 'H') x = +tokens[i++];
        else if (c === 'V') y = +tokens[i++];
        else { x = +tokens[i++]; y = +tokens[i++]; }
        pts.push(pt(x, y));
      }
      const cs = getComputedStyle(p);
      items.push({ type: 'path', pts, closed, fill: hex(cs.fill), stroke: hex(cs.stroke), sw: parseFloat(cs.strokeWidth) * m.a });
    }
    const rects = [...svg.querySelectorAll('rect')].map(r => ({ r, b: r.getBoundingClientRect(), lines: [] }));
    const free = [];
    for (const t of svg.querySelectorAll('text')) {
      const b = t.getBoundingClientRect(), cx = b.left + b.width / 2, cy = b.top + b.height / 2, cs = getComputedStyle(t);
      const line = { y: +t.getAttribute('y'), algn: 'center', lh: parseFloat(cs.fontSize) * m.a * 1.22,
        runs: [{ t: t.textContent, size: parseFloat(cs.fontSize) * m.a, bold: parseInt(cs.fontWeight) >= 600, italic: false, mono: false, color: hex(cs.fill), hl: null }] };
      const host = rects.find(o => cx > o.b.left && cx < o.b.right && cy > o.b.top && cy < o.b.bottom);
      if (host) host.lines.push(line); else free.push({ line, b });
    }
    for (const o of rects) items.push(Object.assign({ type: 'text', paras: o.lines, fill: hex(getComputedStyle(o.r).fill), role: null, pre: false, padL: 8, padR: 8, gapT: 1, gapB: 1 }, box(o.b)));
    if (free.length) {
      const x = Math.min(...free.map(f => f.b.left)), y = Math.min(...free.map(f => f.b.top));
      const r = Math.max(...free.map(f => f.b.right)), b = Math.max(...free.map(f => f.b.bottom));
      items.push({ type: 'text', paras: free.map(f => f.line), fill: null, role: null, pre: false, padL: 0, padR: 0, gapT: 0, gapB: 0, x, y, w: r - x, h: b - y });
    }
  }

  function walk(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    if (el.matches('.head')) {
      // Dải đầu trang nằm trên layout; ở đây chỉ lấy dải mục lục và tiêu đề
      const strip = el.querySelector('.strip');
      items.push(Object.assign({ type: 'strip', names: [...strip.children].map(s => s.textContent), now: [...strip.children].findIndex(s => s.className === 'now') }, box(strip.getBoundingClientRect())));
      const h = el.querySelector('h2');
      emitText(h, [para(h)], null, 'title');
      return;
    }
    if (el.matches('.foot')) {
      const [l, r] = el.children;
      if (l.textContent.trim()) emitText(l, [para(l)], null);
      items.push(Object.assign({ type: 'pageno', total: document.querySelectorAll('.slide').length, color: hex(getComputedStyle(r).color), size: parseFloat(getComputedStyle(r).fontSize) }, box(r.getBoundingClientRect())));
      return;
    }
    // Biểu đồ trang 12 và 23 chuyển thành biểu đồ gốc của PowerPoint
    if (el.querySelector(':scope > .legend')) {
      const bars = el.querySelector('.brow');
      items.push(Object.assign({ type: 'chart', kind: bars ? 'bars' : 'lines', alt: bars ? 'Biểu đồ thanh: MuTAP và Pynguin trên HumanEval và Refactory' : el.querySelector('svg').getAttribute('aria-label') }, box(el.getBoundingClientRect())));
      return;
    }
    if (el.tagName === 'svg') return emitSvg(el);
    if (el.tagName === 'TABLE') return emitTable(el);
    if (el.matches('ul.b')) return emitList(el);
    if (el.matches('.ar')) {
      const b = el.getBoundingClientRect(), cx = b.left + b.width / 2, cy = b.top + b.height / 2;
      items.push({ type: 'path', pts: [[cx - 13, cy - 18], [cx + 13, cy], [cx - 13, cy + 18]], closed: true, fill: '0B6E82', stroke: null, sw: 0 });
      return;
    }
    const fill = hex(cs.backgroundColor);
    const hasText = el.textContent.trim().length > 0;
    if (hasText && onlyInline(el)) {
      const centerFlex = cs.display === 'flex' && cs.justifyContent === 'center';
      emitText(el, [para(el, centerFlex ? { algn: 'center' } : null)], fill, el.tagName === 'H1' ? 'title' : el.matches('.sub') ? 'subtitle' : null);
      emitBorders(el);
      return;
    }
    if (fill && el !== slide) items.push(Object.assign({ type: 'rect', fill }, box(el.getBoundingClientRect())));
    if (el !== slide) emitBorders(el);
    for (const ch of el.children) walk(ch);
  }
  walk(slide);
  return { items, section: Number(slide.dataset.sec || 0), head: slide.querySelector('.head') ? box(slide.querySelector('.head').getBoundingClientRect()) : null };
}
"""


def emu(px):
    return Emu(int(round(px * PX)))


def sub(parent, tag, **attrs):
    el = etree.SubElement(parent, qn(tag))
    for k, v in attrs.items():
        el.set(k, str(v))
    return el


def solid(parent, hex_color):
    sub(sub(parent, "a:solidFill"), "a:srgbClr", val=hex_color)


def half_pt(size_px):
    """Cỡ chữ: px -> phần trăm pt, làm tròn đến 0,5 pt cho gọn khi sửa trong PowerPoint."""
    return int(round(size_px)) * 50


def add_run(p, text, r, underline=None):
    run = sub(p, "a:r")
    rpr = sub(run, "a:rPr", lang="vi-VN", sz=half_pt(r["size"]), dirty="0")
    rpr.set("b", "1" if r.get("bold") else "0")
    rpr.set("i", "1" if r.get("italic") else "0")
    if underline:
        rpr.set("u", "sng")
    if r.get("color"):
        solid(rpr, r["color"])
    if r.get("hl"):
        sub(sub(rpr, "a:highlight"), "a:srgbClr", val=r["hl"])
    if underline:
        solid(sub(rpr, "a:uFill"), underline)
    if r.get("mono"):
        sub(rpr, "a:latin", typeface="Consolas")
        sub(rpr, "a:cs", typeface="Consolas")
    sub(run, "a:t").text = text


ALIGN = {"center": "ctr", "right": "r", "end": "r"}


def add_para(tx_body, para, runs=None):
    p = sub(tx_body, "a:p")
    ppr = sub(p, "a:pPr", algn=ALIGN.get(para.get("algn"), "l"))
    if para.get("bullet"):
        ppr.set("marL", str(int(para["marL"] * PX)))
        ppr.set("indent", str(-int(para["marL"] * PX)))
    else:
        ppr.set("marL", "0")
        ppr.set("indent", "0")
    sub(sub(ppr, "a:lnSpc"), "a:spcPts", val=int(round(para["lh"] * 50)))
    sub(sub(ppr, "a:spcBef"), "a:spcPts", val=int(round(para.get("before", 0) * 50)))
    sub(sub(ppr, "a:spcAft"), "a:spcPts", val=0)
    if para.get("bullet"):
        sub(sub(ppr, "a:buClr"), "a:srgbClr", val="0B6E82")
        sub(ppr, "a:buSzPct", val=70000)
        sub(ppr, "a:buFont", typeface="Arial")
        sub(ppr, "a:buChar", char="■")
    else:
        sub(ppr, "a:buNone")
    for r in (runs if runs is not None else para["runs"]):
        if r.get("br"):
            sub(p, "a:br")
        else:
            text = r["t"]
            if r.get("tag"):
                text = " " + text + " "  # tạo khoảng đệm hai bên nhãn màu
            add_run(p, text, r)
    return p


def add_paras(tx_body, paras):
    """Thay nội dung txBody. Khối code giữ từng dòng thành một đoạn riêng."""
    for p in tx_body.findall(qn("a:p")):
        tx_body.remove(p)
    for para in paras:
        lines = [[]]
        for r in para["runs"]:
            if not r.get("br") and "\n" in r["t"]:
                parts = r["t"].split("\n")
                for i, part in enumerate(parts):
                    if i:
                        lines.append([])
                    if part:
                        lines[-1].append(dict(r, t=part))
            else:
                lines[-1].append(r)
        for line in lines:
            add_para(tx_body, para, line)
    if not paras:
        sub(tx_body, "a:p")


def set_body(tf, l=0, t=0, r=0, b=0, anchor="t", wrap=True):
    body = tf._txBody.find(qn("a:bodyPr"))
    body.attrib.clear()
    for child in list(body):
        body.remove(child)
    body.set("wrap", "square" if wrap else "none")
    for k, v in (("lIns", l), ("tIns", t), ("rIns", r), ("bIns", b)):
        body.set(k, str(int(max(v, 0) * PX)))
    body.set("anchor", anchor)
    body.set("rtlCol", "0")
    sub(body, "a:noAutofit")


def draw_rect(slide, it):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"]))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(it["fill"])
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def draw_text(slide, it):
    # Hình có nền thì căn giữa theo chiều dọc nếu bản HTML căn giữa; hộp chữ thường luôn neo trên
    centered = bool(it.get("fill")) and abs(it["gapT"] - it["gapB"]) < 3
    anchor = "ctr" if centered else "t"
    top = 0 if centered else it["gapT"]
    algn = it["paras"][0].get("algn") if it["paras"] else "left"
    if it.get("fill"):
        s = draw_rect(slide, it)
        l, r = it["padL"], it["padR"]
        if algn not in ("center", "right", "end"):
            r = max(r - 8, 0)  # chừa chút chỗ vì PowerPoint ngắt dòng hơi khác trình duyệt
        else:
            l, r = max(l - 4, 0), max(r - 4, 0)
    else:
        x, w = it["x"], it["w"]
        if algn == "center":
            x, w = x - 6, w + 12
        elif algn in ("right", "end"):
            x, w = x - 12, w + 12
        else:
            w = w + 12
        s = slide.shapes.add_textbox(emu(x), emu(it["y"]), emu(w), emu(it["h"]))
        l, r = it["padL"], 0
    set_body(s.text_frame, l=l, t=top, r=r, anchor=anchor, wrap=not it["pre"])
    add_paras(s.text_frame._txBody, it["paras"])
    return s


def draw_path(slide, it):
    pts = [(int(x * PX), int(y * PX)) for x, y in it["pts"]]
    if len(pts) == 2 and not it["closed"]:
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        c.line.color.rgb = RGBColor.from_string(it["stroke"])
        c.line.width = emu(it["sw"])
        style = c._element.find(qn("p:style"))
        if style is not None:
            c._element.remove(style)  # bỏ kiểu mặc định của connector vì kiểu này kèm bóng đổ
        return
    fb = slide.shapes.build_freeform(pts[0][0], pts[0][1], scale=1.0)
    fb.add_line_segments(pts[1:], close=True)
    s = fb.convert_to_shape()
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(it["fill"])
    s.line.fill.background()
    s.shadow.inherit = False


def draw_table(slide, it):
    rows, cols = len(it["rows"]), len(it["rows"][0]["cells"])
    frame = slide.shapes.add_table(rows, cols, emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"]))
    table = frame.table
    tbl_pr = table._tbl.tblPr
    tbl_pr.attrib.clear()
    for child in list(tbl_pr):
        tbl_pr.remove(child)  # bỏ kiểu bảng mặc định, màu lấy theo từng ô như bản HTML
    for j, cell in enumerate(it["rows"][0]["cells"]):
        table.columns[j].width = emu(cell["w"])
    for i, row in enumerate(it["rows"]):
        table.rows[i].height = emu(row["h"])
        for j, c in enumerate(row["cells"]):
            tc = table.cell(i, j)._tc
            add_paras(tc.txBody, [dict(c["para"], algn=c["align"])])
            old = tc.find(qn("a:tcPr"))
            if old is not None:
                tc.remove(old)
            pr = sub(tc, "a:tcPr", marL=int((c["padL"] - 2) * PX), marR=int((c["padR"] - 2) * PX), marT=int(c["padT"] * PX), marB=int(c["padB"] * PX),
                     anchor="b" if c["valign"] == "bottom" else "ctr")
            for side in ("a:lnL", "a:lnR", "a:lnT"):
                sub(sub(pr, side, w=0), "a:noFill")
            if c["rule"]:
                solid(sub(pr, "a:lnB", w=PX), c["rule"])
            else:
                sub(sub(pr, "a:lnB", w=0), "a:noFill")
            if c["fill"]:
                solid(pr, c["fill"])
            else:
                sub(pr, "a:noFill")


def draw_strip(slide, it):
    s = slide.shapes.add_textbox(emu(it["x"]), emu(it["y"] - 2), emu(it["w"]), emu(it["h"] + 6))
    set_body(s.text_frame, anchor="t")
    tx = s.text_frame._txBody
    for p in tx.findall(qn("a:p")):
        tx.remove(p)
    p = sub(tx, "a:p")
    sub(p, "a:pPr", algn="l")
    gap = {"size": 23, "color": "A9C3D3"}
    for k, name in enumerate(it["names"]):
        if k:
            add_run(p, " " * 5, gap)
        if k == it["now"]:
            add_run(p, name, {"size": 23, "bold": True, "color": "FFFFFF"}, underline="FFB938")
        else:
            add_run(p, name, gap)


def draw_pageno(slide, it, number):
    s = slide.shapes.add_textbox(emu(it["x"] - 12), emu(it["y"]), emu(it["w"] + 12), emu(it["h"]))
    set_body(s.text_frame, anchor="ctr")
    tx = s.text_frame._txBody
    for p in tx.findall(qn("a:p")):
        tx.remove(p)
    p = sub(tx, "a:p")
    sub(p, "a:pPr", algn="r")
    # Số trang là trường tự động, tự đúng khi thêm hoặc bớt slide
    fld = sub(p, "a:fld", id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", type="slidenum")
    rpr = sub(fld, "a:rPr", lang="vi-VN", sz=half_pt(it["size"]))
    solid(rpr, it["color"])
    sub(fld, "a:t").text = str(number)
    add_run(p, " / %d" % it["total"], {"size": it["size"], "color": it["color"]})


def style_chart(chart):
    chart.font.size = Pt(14)
    chart.font.color.rgb = RGBColor.from_string("1A2433")
    chart.has_title = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.TOP
    chart.legend.include_in_layout = False


def custom_label(point, text, position, size=15, color="1A2433"):
    dl = point.data_label
    dl.has_text_frame = True
    dl.text_frame.text = text
    run = dl.text_frame.paragraphs[0].runs[0]
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(color)
    dl.position = position


def draw_chart(slide, it):
    data = CategoryChartData()
    x, y, w, h = emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"])
    if it["kind"] == "bars":
        # Số liệu giống trang 12 của bản HTML; nhãn ghi dấu phẩy thập phân kiểu Việt Nam
        data.categories = ["HumanEval: mutation score", "Refactory: phát hiện lỗi thật của sinh viên"]
        data.add_series("MuTAP", (93.57, 94.91))
        data.add_series("Pynguin (không dùng LLM)", (65.94, 67.54))
        frame = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, x, y, w, h, data)
        chart = frame.chart
        style_chart(chart)
        chart.category_axis.reverse_order = True
        chart.category_axis.format.line.color.rgb = RGBColor.from_string("D3DAE1")
        chart.category_axis.tick_labels.font.size = Pt(15)
        chart.category_axis.tick_labels.font.bold = True
        va = chart.value_axis
        va.minimum_scale, va.maximum_scale = 0, 100
        va.major_unit = 25
        va.has_major_gridlines = False
        va.tick_label_position = XL_TICK_LABEL_POSITION.NONE
        va.format.line.fill.background()
        plot = chart.plots[0]
        plot.gap_width, plot.overlap = 45, -8
        # Nhãn đặt trong thanh để trục giữ đúng thang 0-100 như ghi ở chân trang
        labels = [("0B6E82", "FFFFFF", ("93,57 %", "94,91 %")), ("D08A16", "1A2433", ("65,94 %", "67,54 %"))]
        for series, (color, label_color, texts) in zip(plot.series, labels):
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = RGBColor.from_string(color)
            for i, text in enumerate(texts):
                custom_label(series.points[i], text, XL_LABEL_POSITION.INSIDE_END, color=label_color)
    else:
        data.categories = ["B: chưa có mutation", "C: có mutation"]
        data.add_series("Mutant LLM chưa thấy (held-out)", (91.8, 91.8))
        data.add_series("Tất cả mutant, như MuTAP", (83.0, 86.0))
        frame = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, x, y, w, h, data)
        chart = frame.chart
        style_chart(chart)
        chart.category_axis.tick_labels.font.size = Pt(15)
        chart.category_axis.tick_labels.font.bold = True
        chart.category_axis.format.line.color.rgb = RGBColor.from_string("D3DAE1")
        va = chart.value_axis
        va.minimum_scale, va.maximum_scale = 80, 95
        va.major_unit = 5
        va.tick_labels.number_format = '0" %"'
        va.tick_labels.number_format_is_linked = False
        va.major_gridlines.format.line.color.rgb = RGBColor.from_string("D3DAE1")
        va.format.line.fill.background()
        specs = [("0B6E82", ("91,8", "91,8"), XL_LABEL_POSITION.ABOVE), ("D08A16", ("83,0", "86,0"), XL_LABEL_POSITION.BELOW)]
        for series, (color, texts, pos) in zip(chart.plots[0].series, specs):
            series.smooth = False
            series.format.line.color.rgb = RGBColor.from_string(color)
            series.format.line.width = Pt(3)
            series.marker.style = XL_MARKER_STYLE.CIRCLE
            series.marker.size = 13
            series.marker.format.fill.solid()
            series.marker.format.fill.fore_color.rgb = RGBColor.from_string(color)
            series.marker.format.line.color.rgb = RGBColor.from_string("FFFFFF")
            for i, text in enumerate(texts):
                custom_label(series.points[i], text, pos, size=20)
    frame._element.nvGraphicFramePr.cNvPr.set("descr", it["alt"])


def patch_theme(prs):
    """Đặt font và bảng màu của theme theo bản HTML để bảng chọn màu trong PowerPoint khớp với slide."""
    part = next(rel.target_part for rel in prs.slide_master.part.rels.values() if rel.reltype.endswith("/theme"))
    xml = part.blob.decode("utf-8")
    xml = re.sub(r'(<a:(?:majorFont|minorFont)>\s*<a:latin typeface=")[^"]*', r"\1Arial", xml)
    xml = re.sub(r'<a:font script="[^"]*" typeface="[^"]*"/>', "", xml)
    colors = {"dk2": "12384F", "lt2": "F2F5F7", "accent1": "0B6E82", "accent2": "D08A16", "accent3": "1E7B4F",
              "accent4": "B92D2D", "accent5": "A86200", "accent6": "4B5A6B"}
    for name, val in colors.items():
        xml = re.sub(r"(<a:%s>).*?(</a:%s>)" % (name, name), r'\g<1><a:srgbClr val="%s"/>\g<2>' % val, xml, flags=re.S)
    xml = re.sub(r"(<a:dk1>).*?(</a:dk1>)", r'\g<1><a:srgbClr val="1A2433"/>\g<2>', xml, flags=re.S)
    xml = re.sub(r"(<a:lt1>).*?(</a:lt1>)", r'\g<1><a:srgbClr val="FFFFFF"/>\g<2>', xml, flags=re.S)
    part._blob = xml.encode("utf-8")


def style_layout_title(ph, x, y, w, h, size_pt, color):
    ph.left, ph.top, ph.width, ph.height = emu(x), emu(y), emu(w), emu(h)
    set_body(ph.text_frame, anchor="t")
    lst = ph.text_frame._txBody.find(qn("a:lstStyle"))
    for child in list(lst):
        lst.remove(child)
    lvl = sub(lst, "a:lvl1pPr", marL=0, indent=0, algn="l")
    sub(lvl, "a:buNone")
    rpr = sub(lvl, "a:defRPr", sz=int(size_pt * 100), b=1)
    solid(rpr, color)


def build_layouts(prs, head, cover_items):
    """Giữ 2 layout: Bìa và Nội dung. Dải đầu trang và đường kẻ chân trang nằm trên layout."""
    master = prs.slide_master
    for ph in master.placeholders:  # file mẫu của python-pptx là 4:3, kéo về khổ 16:9
        ph.left, ph.width = emu(72), emu(1776)
    keep = {"Title Slide": "Bìa", "Title Only": "Nội dung"}
    for layout in list(prs.slide_layouts):
        if layout.name not in keep:
            prs.slide_layouts.remove(layout)
    cover, content = prs.slide_layouts[0], prs.slide_layouts[1]
    cover.name, content.name = "Bìa", "Nội dung"
    for layout in (cover, content):
        for ph in list(layout.placeholders):
            if ph.placeholder_format.type is not None and ph.placeholder_format.idx in (10, 11, 12):
                ph._element.getparent().remove(ph._element)

    # Layout bìa: nền xanh đậm, tiêu đề và phụ đề theo vị trí đo được
    bg = cover.background.fill
    bg.solid()
    bg.fore_color.rgb = RGBColor.from_string("12384F")
    title = next(i for i in cover_items if i.get("role") == "title")
    subtitle = next(i for i in cover_items if i.get("role") == "subtitle")
    phs = list(cover.placeholders)
    style_layout_title(phs[0], title["x"], title["y"], title["w"], title["h"], 40, "FFFFFF")
    style_layout_title(phs[1], subtitle["x"], subtitle["y"], subtitle["w"], subtitle["h"], 20, "CFE0EA")

    # Layout nội dung: dải đầu trang và đường kẻ chân trang
    sp_tree = content.shapes._spTree
    for spec in (dict(x=0, y=0, w=1920, h=head["h"], fill="12384F", name="Dải đầu trang"),
                 dict(x=0, y=1030, w=1920, h=1, fill="D3DAE1", name="Đường kẻ chân trang")):
        sp = make_layout_rect(spec)
        sp_tree.insert(2, sp)
    return cover, content


def make_layout_rect(spec):
    xml = (
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="%s">'
        '<p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr userDrawn="1"/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="vi-VN"/></a:p></p:txBody></p:sp>'
    ) % (A, 100 + spec["y"], spec["name"], spec["x"] * PX, spec["y"] * PX, spec["w"] * PX, spec["h"] * PX, spec["fill"])
    return etree.fromstring(xml)


def fill_placeholder(ph, it):
    """Đưa chữ vào placeholder để PowerPoint nhận đúng tiêu đề (Outline View, trình đọc màn hình)."""
    set_body(ph.text_frame, anchor="t")
    add_paras(ph.text_frame._txBody, it["paras"])


def add_sections(prs, slide_sections):
    """Chia slide theo các phần của bài trình bày (khung Section trong PowerPoint)."""
    p14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
    ids = list(prs.part._element.sldIdLst)
    ext_lst = prs.part._element.find(qn("p:extLst"))
    if ext_lst is None:
        ext_lst = sub(prs.part._element, "p:extLst")
    ext = sub(ext_lst, "p:ext", uri="{521415D9-36F7-43E2-AB2F-B90AF26B5E84}")
    lst = etree.SubElement(ext, "{%s}sectionLst" % p14, nsmap={"p14": p14})
    for k, name in enumerate(SECTIONS):
        sec = etree.SubElement(lst, "{%s}section" % p14, name=name, id="{A1B2C3D4-0000-4000-8000-00000000%04d}" % k)
        sld_lst = etree.SubElement(sec, "{%s}sldIdLst" % p14)
        for sld, s in zip(ids, slide_sections):
            if s == k:
                etree.SubElement(sld_lst, "{%s}sldId" % p14, id=sld.get("id"))


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(HTML.as_uri())
        page.add_style_tag(content=FONT_OVERRIDE)
        page.evaluate("document.fonts.ready")
        n = page.evaluate("document.querySelectorAll('.slide').length")
        slides = []
        for i in range(n):
            page.evaluate("(i) => { location.hash = '#' + (i + 1); }", i)
            page.wait_for_function("(i) => document.querySelectorAll('.slide')[i].classList.contains('on')", arg=i)
            slides.append(page.evaluate(EXTRACT_JS, i))
        browser.close()

    heads = {round(s["head"]["h"]) for s in slides if s["head"]}
    if len(heads) != 1:
        print("Cảnh báo: chiều cao dải đầu trang khác nhau:", heads)

    prs = Presentation()
    prs.slide_width, prs.slide_height = emu(1920), emu(1080)
    prs.core_properties.title = "LLM Agent tự sinh unit test đa ngôn ngữ"
    prs.core_properties.subject = "Báo cáo đồ án cuối kỳ, 2026"
    prs.core_properties.author = ""
    patch_theme(prs)
    cover, content = build_layouts(prs, slides[1]["head"], slides[0]["items"])

    for number, data in enumerate(slides, 1):
        layout = cover if number == 1 else content
        slide = prs.slides.add_slide(layout)
        phs = {ph.placeholder_format.idx: ph for ph in slide.placeholders}
        for it in data["items"]:
            kind = it["type"]
            if kind == "text" and it.get("role") == "title":
                ph = slide.shapes.title
                if number > 1:
                    ph.left, ph.top, ph.width, ph.height = emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"])
                fill_placeholder(ph, it)
            elif kind == "text" and it.get("role") == "subtitle":
                fill_placeholder(phs[1], it)
            elif kind == "text":
                draw_text(slide, it)
            elif kind == "rect":
                draw_rect(slide, it)
            elif kind == "path":
                draw_path(slide, it)
            elif kind == "table":
                draw_table(slide, it)
            elif kind == "strip":
                draw_strip(slide, it)
            elif kind == "pageno":
                draw_pageno(slide, it, number)
            elif kind == "chart":
                draw_chart(slide, it)
            else:
                sys.exit("Không biết phần tử: " + kind)

    add_sections(prs, [s["section"] for s in slides])
    prs.save(OUT)
    print("Đã ghi", OUT, "-", len(slides), "trang")


if __name__ == "__main__":
    main()
