/**
 * SVG renderer for the automaton diagram.
 *
 * Replaces the QGraphicsView canvas of the desktop app: states are draggable
 * circles, transitions are straight lines, quadratic curves (when a pair of
 * states is connected both ways) or self-loops, and the whole scene pans and
 * zooms. Every visual attribute is written directly on the element rather
 * than through a CSS class, so the SVG can be serialized straight to PNG.
 */

const STATE_RADIUS = 28;
const ARROW_SIZE = 10;

const GRAPH_COLORS = {
  normal: "#4a90d9",
  accept: "#2e9e5b",
  startRing: "#e08a1e",
  highlight: "#e0483e",
  dead: "#8a8f98",
  unreachableBorder: "#c94f4f",
  stateText: "#ffffff",
  stateBorder: "#1c1e21",
  edgeLight: "#5c6470",
  edgeDark: "#aab2c0",
  edgeTextLight: "#333844",
  edgeTextDark: "#e6e6e6",
};

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  if (attrs) {
    for (const key of Object.keys(attrs)) {
      el.setAttribute(key, String(attrs[key]));
    }
  }
  return el;
}

class GraphView {
  /**
   * @param {SVGSVGElement} svg     the canvas element
   * @param {object} callbacks      { onStateMoved, onStateSelected, onStateDoubleClick }
   */
  constructor(svg, callbacks) {
    this.svg = svg;
    this.callbacks = callbacks || {};
    this.automaton = null;
    this.darkMode = false;

    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;

    this.selectedState = null;
    this.highlightedStates = new Set();
    this.highlightedEdges = new Set();
    this.deadStates = new Set();
    this.unreachableStates = new Set();

    this.stateNodes = {};
    this.edgeRecords = [];

    this.dragging = null;
    this.panning = null;

    this.defs = svgEl("defs");
    this.svg.appendChild(this.defs);
    this.buildMarkers();

    this.viewport = svgEl("g", { id: "viewport" });
    this.svg.appendChild(this.viewport);
    this.edgeLayer = svgEl("g");
    this.nodeLayer = svgEl("g");
    this.viewport.appendChild(this.edgeLayer);
    this.viewport.appendChild(this.nodeLayer);

    this.bindEvents();
  }

  buildMarkers() {
    const makeMarker = (id, color) => {
      const marker = svgEl("marker", {
        id: id,
        viewBox: "0 0 10 10",
        refX: 9,
        refY: 5,
        markerWidth: ARROW_SIZE * 0.8,
        markerHeight: ARROW_SIZE * 0.8,
        orient: "auto-start-reverse",
        markerUnits: "userSpaceOnUse",
      });
      marker.appendChild(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: color }));
      return marker;
    };
    this.defs.appendChild(makeMarker("arrow-light", GRAPH_COLORS.edgeLight));
    this.defs.appendChild(makeMarker("arrow-dark", GRAPH_COLORS.edgeDark));
    this.defs.appendChild(makeMarker("arrow-highlight", GRAPH_COLORS.highlight));
    this.defs.appendChild(makeMarker("arrow-start", GRAPH_COLORS.startRing));
  }

  get edgeColor() {
    return this.darkMode ? GRAPH_COLORS.edgeDark : GRAPH_COLORS.edgeLight;
  }

  get edgeTextColor() {
    return this.darkMode ? GRAPH_COLORS.edgeTextDark : GRAPH_COLORS.edgeTextLight;
  }

  get arrowMarker() {
    return this.darkMode ? "arrow-dark" : "arrow-light";
  }

  setDarkMode(enabled) {
    this.darkMode = enabled;
    this.render();
  }

  setAutomaton(automaton) {
    this.automaton = automaton;
    this.render();
  }

  /* ---------------------------------------------------------------- */
  /* Coordinate helpers                                                */
  /* ---------------------------------------------------------------- */

  applyTransform() {
    this.viewport.setAttribute(
      "transform",
      "translate(" + this.offsetX + "," + this.offsetY + ") scale(" + this.scale + ")"
    );
  }

  /** Convert a mouse event into scene coordinates. */
  toSceneCoords(event) {
    const rect = this.svg.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - this.offsetX) / this.scale,
      y: (event.clientY - rect.top - this.offsetY) / this.scale,
    };
  }

  positionOf(state) {
    const p = this.automaton.positions[state];
    return p ? { x: p[0], y: p[1] } : { x: 0, y: 0 };
  }

  /* ---------------------------------------------------------------- */
  /* Layout                                                            */
  /* ---------------------------------------------------------------- */

  /** Circular auto-layout, same formula as the desktop app. */
  autoLayout() {
    const automaton = this.automaton;
    const n = automaton.states.length;
    if (!n) return;
    const radius = Math.max(150, 60 * n);
    const cx = radius + 60;
    const cy = radius + 60;
    automaton.states.forEach((state, i) => {
      const angle = (2 * Math.PI * i) / n;
      automaton.positions[state] = [
        cx + radius * Math.cos(angle),
        cy + radius * Math.sin(angle),
      ];
    });
    this.render();
    this.fitView();
  }

  /** Give a circular position to any state that does not have one yet. */
  ensurePositions() {
    const automaton = this.automaton;
    const missing = automaton.states.filter((s) => !(s in automaton.positions));
    if (!missing.length) return;
    const n = automaton.states.length;
    const radius = Math.max(150, 55 * n);
    const cx = radius + 60;
    const cy = radius + 60;
    automaton.states.forEach((state, i) => {
      if (!(state in automaton.positions)) {
        const angle = (2 * Math.PI * i) / n;
        automaton.positions[state] = [
          cx + radius * Math.cos(angle),
          cy + radius * Math.sin(angle),
        ];
      }
    });
  }

  contentBounds() {
    if (!this.automaton || !this.automaton.states.length) return null;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const state of this.automaton.states) {
      const p = this.positionOf(state);
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    const pad = STATE_RADIUS + 70;
    return {
      x: minX - pad,
      y: minY - pad,
      width: maxX - minX + pad * 2,
      height: maxY - minY + pad * 2,
    };
  }

  fitView() {
    const bounds = this.contentBounds();
    if (!bounds) return;
    const rect = this.svg.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const scale = Math.min(rect.width / bounds.width, rect.height / bounds.height, 1.6);
    this.scale = scale;
    this.offsetX = (rect.width - bounds.width * scale) / 2 - bounds.x * scale;
    this.offsetY = (rect.height - bounds.height * scale) / 2 - bounds.y * scale;
    this.applyTransform();
  }

  zoomBy(factor, centerClient) {
    const rect = this.svg.getBoundingClientRect();
    const cx = centerClient ? centerClient.x - rect.left : rect.width / 2;
    const cy = centerClient ? centerClient.y - rect.top : rect.height / 2;
    const sceneX = (cx - this.offsetX) / this.scale;
    const sceneY = (cy - this.offsetY) / this.scale;
    this.scale = Math.min(4, Math.max(0.15, this.scale * factor));
    this.offsetX = cx - sceneX * this.scale;
    this.offsetY = cy - sceneY * this.scale;
    this.applyTransform();
  }

  resetZoom() {
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.applyTransform();
  }

  /* ---------------------------------------------------------------- */
  /* Rendering                                                         */
  /* ---------------------------------------------------------------- */

  render() {
    if (!this.automaton) return;
    this.ensurePositions();
    this.edgeLayer.textContent = "";
    this.nodeLayer.textContent = "";
    this.stateNodes = {};
    this.edgeRecords = [];

    this.renderEdges();
    this.renderStates();
    this.applyTransform();
  }

  /** Group transitions by (source, target) so parallel symbols share one arrow. */
  groupedEdges() {
    const groups = new Map();
    for (const row of this.automaton.allTransitionRows()) {
      const key = row[0] + KEY_SEP + row[2];
      if (!groups.has(key)) {
        groups.set(key, { source: row[0], target: row[2], symbols: [] });
      }
      groups.get(key).symbols.push(row[1]);
    }
    return Array.from(groups.values());
  }

  renderEdges() {
    const groups = this.groupedEdges();
    const pairKeys = new Set(groups.map((g) => g.source + KEY_SEP + g.target));

    for (const group of groups) {
      const isSelfLoop = group.source === group.target;
      const hasReverse =
        !isSelfLoop && pairKeys.has(group.target + KEY_SEP + group.source);
      const curvature = hasReverse ? 0.22 : 0;
      const label = group.symbols.join(", ");
      const record = this.createEdge(group.source, group.target, label, curvature, isSelfLoop);
      this.edgeRecords.push(record);
    }
  }

  createEdge(source, target, label, curvature, isSelfLoop) {
    const path = svgEl("path", {
      fill: "none",
      stroke: this.edgeColor,
      "stroke-width": 2,
      "marker-end": "url(#" + this.arrowMarker + ")",
    });
    const text = svgEl("text", {
      "text-anchor": "middle",
      "dominant-baseline": "middle",
      "font-family": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      "font-size": 13,
      fill: this.edgeTextColor,
    });
    text.textContent = label;

    this.edgeLayer.appendChild(path);
    this.edgeLayer.appendChild(text);

    const record = {
      source: source,
      target: target,
      label: label,
      curvature: curvature,
      isSelfLoop: isSelfLoop,
      path: path,
      text: text,
      highlighted: false,
    };
    this.updateEdgeGeometry(record);
    return record;
  }

  updateEdgeGeometry(record) {
    const sp = this.positionOf(record.source);

    if (record.isSelfLoop) {
      const cx = sp.x;
      const cy = sp.y;
      const d =
        "M " + (cx - 14) + " " + (cy - STATE_RADIUS + 4) +
        " C " + (cx - 32) + " " + (cy - STATE_RADIUS - 46) +
        ", " + (cx + 32) + " " + (cy - STATE_RADIUS - 46) +
        ", " + (cx + 14) + " " + (cy - STATE_RADIUS + 4);
      record.path.setAttribute("d", d);
      record.text.setAttribute("x", cx);
      record.text.setAttribute("y", cy - STATE_RADIUS - 44);
      return;
    }

    const tp = this.positionOf(record.target);
    const dx = tp.x - sp.x;
    const dy = tp.y - sp.y;
    const dist = Math.hypot(dx, dy) || 1;
    const ux = dx / dist;
    const uy = dy / dist;

    const start = { x: sp.x + ux * STATE_RADIUS, y: sp.y + uy * STATE_RADIUS };
    const end = { x: tp.x - ux * STATE_RADIUS, y: tp.y - uy * STATE_RADIUS };
    const mid = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };

    if (record.curvature) {
      const perpX = -uy * dist * record.curvature;
      const perpY = ux * dist * record.curvature;
      const ctrl = { x: mid.x + perpX, y: mid.y + perpY };
      record.path.setAttribute(
        "d",
        "M " + start.x + " " + start.y + " Q " + ctrl.x + " " + ctrl.y + " " + end.x + " " + end.y
      );
      // Label sits on the curve, slightly outside its apex.
      record.text.setAttribute("x", mid.x + perpX * 0.62);
      record.text.setAttribute("y", mid.y + perpY * 0.62);
    } else {
      record.path.setAttribute("d", "M " + start.x + " " + start.y + " L " + end.x + " " + end.y);
      record.text.setAttribute("x", mid.x - uy * 14);
      record.text.setAttribute("y", mid.y + ux * 14 - 4);
    }
  }

  renderStates() {
    for (const state of this.automaton.states) {
      this.nodeLayer.appendChild(this.createStateNode(state));
    }
  }

  createStateNode(state) {
    const pos = this.positionOf(state);
    const group = svgEl("g", {
      transform: "translate(" + pos.x + "," + pos.y + ")",
      cursor: "grab",
    });

    const isStart = this.automaton.startState === state;
    const isAccept = this.automaton.acceptStates.has(state);
    const isDead = this.deadStates.has(state);
    const isUnreachable = this.unreachableStates.has(state);
    const isHighlighted = this.highlightedStates.has(state);
    const isSelected = this.selectedState === state;

    let fill = GRAPH_COLORS.normal;
    if (isHighlighted) fill = GRAPH_COLORS.highlight;
    else if (isDead) fill = GRAPH_COLORS.dead;
    else if (isAccept) fill = GRAPH_COLORS.accept;

    let strokeColor = isStart ? GRAPH_COLORS.startRing : GRAPH_COLORS.stateBorder;
    let strokeWidth = isStart ? 3 : 2;
    let dash = null;
    if (isUnreachable) {
      strokeColor = GRAPH_COLORS.unreachableBorder;
      dash = "6 4";
    }

    // Incoming arrow that marks the start state.
    if (isStart) {
      const arrow = svgEl("path", {
        d: "M " + (-STATE_RADIUS - 34) + " 0 L " + (-STATE_RADIUS - 4) + " 0",
        stroke: GRAPH_COLORS.startRing,
        "stroke-width": 3,
        fill: "none",
        "marker-end": "url(#arrow-start)",
      });
      group.appendChild(arrow);
    }

    if (isSelected) {
      group.appendChild(
        svgEl("circle", {
          r: STATE_RADIUS + 6,
          fill: "none",
          stroke: GRAPH_COLORS.startRing,
          "stroke-width": 1.5,
          "stroke-dasharray": "3 3",
          opacity: 0.9,
        })
      );
    }

    const circleAttrs = {
      r: STATE_RADIUS,
      fill: fill,
      stroke: strokeColor,
      "stroke-width": strokeWidth,
    };
    if (dash) circleAttrs["stroke-dasharray"] = dash;
    group.appendChild(svgEl("circle", circleAttrs));

    // Accepting states get the classic inner ring.
    if (isAccept) {
      group.appendChild(
        svgEl("circle", {
          r: STATE_RADIUS - 5,
          fill: "none",
          stroke: strokeColor,
          "stroke-width": strokeWidth,
        })
      );
    }

    const label = svgEl("text", {
      "text-anchor": "middle",
      "dominant-baseline": "central",
      "font-family": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      "font-size": state.length > 6 ? 10 : 13,
      "font-weight": "600",
      fill: GRAPH_COLORS.stateText,
      "pointer-events": "none",
    });
    label.textContent = state.length > 12 ? state.slice(0, 11) + "…" : state;
    group.appendChild(label);

    const title = svgEl("title");
    title.textContent = state;
    group.appendChild(title);

    group.addEventListener("pointerdown", (e) => this.onStatePointerDown(e, state));
    group.addEventListener("dblclick", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (this.callbacks.onStateDoubleClick) this.callbacks.onStateDoubleClick(state);
    });

    this.stateNodes[state] = group;
    return group;
  }

  /* ---------------------------------------------------------------- */
  /* Interaction                                                       */
  /* ---------------------------------------------------------------- */

  bindEvents() {
    this.svg.addEventListener("pointerdown", (e) => this.onBackgroundPointerDown(e));
    window.addEventListener("pointermove", (e) => this.onPointerMove(e));
    window.addEventListener("pointerup", (e) => this.onPointerUp(e));
    this.svg.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
        this.zoomBy(factor, { x: e.clientX, y: e.clientY });
      },
      { passive: false }
    );
  }

  onStatePointerDown(event, state) {
    event.stopPropagation();
    if (event.button !== 0) return;
    const scene = this.toSceneCoords(event);
    const pos = this.positionOf(state);
    this.dragging = {
      state: state,
      dx: scene.x - pos.x,
      dy: scene.y - pos.y,
      moved: false,
    };
    this.selectState(state);
  }

  onBackgroundPointerDown(event) {
    if (event.button !== 0) return;
    this.panning = {
      startX: event.clientX,
      startY: event.clientY,
      originX: this.offsetX,
      originY: this.offsetY,
    };
    this.selectState(null);
  }

  onPointerMove(event) {
    if (this.dragging) {
      const scene = this.toSceneCoords(event);
      const state = this.dragging.state;
      this.automaton.positions[state] = [
        scene.x - this.dragging.dx,
        scene.y - this.dragging.dy,
      ];
      this.dragging.moved = true;
      this.updateStatePosition(state);
      return;
    }
    if (this.panning) {
      this.offsetX = this.panning.originX + (event.clientX - this.panning.startX);
      this.offsetY = this.panning.originY + (event.clientY - this.panning.startY);
      this.applyTransform();
    }
  }

  onPointerUp() {
    if (this.dragging && this.dragging.moved && this.callbacks.onStateMoved) {
      this.callbacks.onStateMoved(this.dragging.state);
    }
    this.dragging = null;
    this.panning = null;
  }

  /** Move one node without rebuilding the whole scene (keeps dragging smooth). */
  updateStatePosition(state) {
    const node = this.stateNodes[state];
    if (!node) return;
    const pos = this.positionOf(state);
    node.setAttribute("transform", "translate(" + pos.x + "," + pos.y + ")");
    for (const record of this.edgeRecords) {
      if (record.source === state || record.target === state) {
        this.updateEdgeGeometry(record);
      }
    }
  }

  selectState(state) {
    if (this.selectedState === state) return;
    this.selectedState = state;
    this.render();
    if (this.callbacks.onStateSelected) this.callbacks.onStateSelected(state);
  }

  /* ---------------------------------------------------------------- */
  /* Highlighting (simulation and property analysis)                   */
  /* ---------------------------------------------------------------- */

  /**
   * Highlight the active states of a simulation step and the edges that
   * carried the transition into them.
   */
  setHighlight(states, symbol, fromStates) {
    this.highlightedStates = new Set(states || []);
    this.highlightedEdges = new Set();
    if (symbol && fromStates) {
      for (const src of fromStates) {
        for (const dst of this.automaton.targets(src, symbol)) {
          if (this.highlightedStates.has(dst)) {
            this.highlightedEdges.add(src + KEY_SEP + dst);
          }
        }
      }
    }
    this.render();
    this.applyEdgeHighlight();
  }

  clearHighlight() {
    this.highlightedStates = new Set();
    this.highlightedEdges = new Set();
    this.render();
  }

  applyEdgeHighlight() {
    for (const record of this.edgeRecords) {
      const key = record.source + KEY_SEP + record.target;
      const on = this.highlightedEdges.has(key);
      record.path.setAttribute("stroke", on ? GRAPH_COLORS.highlight : this.edgeColor);
      record.path.setAttribute("stroke-width", on ? 3 : 2);
      record.path.setAttribute(
        "marker-end",
        "url(#" + (on ? "arrow-highlight" : this.arrowMarker) + ")"
      );
      record.text.setAttribute("fill", on ? GRAPH_COLORS.highlight : this.edgeTextColor);
    }
  }

  setDiagnostics(deadStates, unreachableStates) {
    this.deadStates = new Set(deadStates || []);
    this.unreachableStates = new Set(unreachableStates || []);
    this.render();
  }

  /* ---------------------------------------------------------------- */
  /* PNG export                                                        */
  /* ---------------------------------------------------------------- */

  /** Serialize the current diagram into a standalone SVG string. */
  toStandaloneSvg(backgroundColor) {
    const bounds = this.contentBounds() || { x: 0, y: 0, width: 400, height: 300 };
    const clone = this.svg.cloneNode(true);
    clone.setAttribute("xmlns", SVG_NS);
    clone.setAttribute("width", Math.round(bounds.width));
    clone.setAttribute("height", Math.round(bounds.height));
    clone.setAttribute(
      "viewBox",
      bounds.x + " " + bounds.y + " " + bounds.width + " " + bounds.height
    );
    const viewport = clone.querySelector("#viewport");
    if (viewport) viewport.removeAttribute("transform");

    const bg = svgEl("rect", {
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
      fill: backgroundColor || "#ffffff",
    });
    clone.insertBefore(bg, clone.firstChild.nextSibling);

    return new XMLSerializer().serializeToString(clone);
  }

  /** Render the diagram to a PNG blob at the given pixel ratio. */
  toPngBlob(backgroundColor, ratio) {
    const scale = ratio || 2;
    const bounds = this.contentBounds() || { x: 0, y: 0, width: 400, height: 300 };
    const svgText = this.toStandaloneSvg(backgroundColor);
    const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(bounds.width * scale);
        canvas.height = Math.round(bounds.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = backgroundColor || "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        canvas.toBlob((out) => {
          if (out) resolve(out);
          else reject(new Error("The browser could not produce the PNG."));
        }, "image/png");
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("The diagram could not be rendered."));
      };
      image.src = url;
    });
  }
}
