import * as THREE from 'three'
import type { ThreeContext } from './useThreeScene'

// ── Palette: Premium dark-tech ──
const WHITE = 0xffffff
const WARM_WHITE = 0xf0f4ff
const EDGE = 0x475569
const EDGE_LIGHT = 0x94a3b8
const GREEN = 0x6366f1       // Indigo accent
const GREEN_BRIGHT = 0x818cf8 // Lighter indigo
const GREEN_DARK = 0x4f46e5   // Deep indigo
const FAINT = 0xe2e8f0

// ── Materials ──

function glassMat(opacity = 0.94): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color: WARM_WHITE, metalness: 0.02, roughness: 0.12,
    transparent: true, opacity, clearcoat: 0.15, clearcoatRoughness: 0.3,
    reflectivity: 0.1,
  })
}

function edgeMat(color = EDGE): THREE.LineBasicMaterial {
  return new THREE.LineBasicMaterial({ color })
}

function addEdges(mesh: THREE.Mesh, color = EDGE): THREE.LineSegments {
  const seg = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 15), edgeMat(color))
  mesh.add(seg)
  return seg
}

// Platform with real thickness + shadow plane beneath
function makePlatform(w: number, h: number, d: number, opacity = 0.94): THREE.Group {
  const g = new THREE.Group()
  const box = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), glassMat(opacity))
  addEdges(box)
  g.add(box)
  return g
}

// ── Drawing helpers ──

function drawLine(pts: THREE.Vector3[], color = EDGE): THREE.Line {
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color }))
}

// ── High-res sprite labels ──

function makeLabel(text: string, size = 0.3, color = '#1a1a1a', bold = false): THREE.Sprite {
  const canvas = document.createElement('canvas')
  const dpr = 6
  const ctx = canvas.getContext('2d')!
  const px = Math.round(size * 100 * dpr)
  ctx.font = `${bold ? '700' : '500'} ${px}px "Inter", "SF Pro Display", system-ui, sans-serif`
  const m = ctx.measureText(text)
  canvas.width = Math.ceil(m.width) + 12 * dpr
  canvas.height = Math.ceil(px * 1.35)
  ctx.font = `${bold ? '700' : '500'} ${px}px "Inter", "SF Pro Display", system-ui, sans-serif`
  ctx.fillStyle = color
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 6 * dpr, canvas.height / 2)
  const tex = new THREE.CanvasTexture(canvas)
  tex.minFilter = THREE.LinearFilter
  tex.anisotropy = 4
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(mat)
  const aspect = canvas.width / canvas.height
  sprite.scale.set(size * aspect, size, 1)
  return sprite
}

// ── Top Layer (y=5.5) ──

function buildTopLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = 5.5

  const panels = [
    { id: 'platform:analytics', label: 'ANALYTICS', x: -4.6 },
    { id: 'platform:workflows', label: 'WORKFLOWS', x: 0 },
    { id: 'platform:integrations', label: 'INTEGRATIONS', x: 4.6 },
  ]

  for (const p of panels) {
    const plat = makePlatform(3.6, 0.22, 2.6)
    plat.position.set(p.x, 0, 0)
    plat.rotation.x = -0.06
    const box = plat.children[0] as THREE.Mesh
    box.userData = { id: p.id, type: 'platform', label: p.label }
    ctx.interactables.set(p.id, box)
    group.add(plat)

    // Title
    const title = makeLabel(p.label, 0.2, '#1a1a1a', true)
    title.position.set(p.x, 0.35, -1.1)
    group.add(title)
  }

  // Analytics — chart lines
  const ag = new THREE.Group()
  ag.position.set(-4.6, 0.2, 0)
  ag.rotation.x = -0.06
  // Axis
  ag.add(drawLine([new THREE.Vector3(-1.3, 0, 0.15), new THREE.Vector3(-1.3, 0, -0.85)], EDGE_LIGHT))
  ag.add(drawLine([new THREE.Vector3(-1.3, 0, 0.15), new THREE.Vector3(1.4, 0, 0.15)], EDGE_LIGHT))
  // Green chart line
  ag.add(drawLine([
    new THREE.Vector3(-1.2, 0.01, -0.1), new THREE.Vector3(-0.6, 0.01, -0.5),
    new THREE.Vector3(-0.1, 0.01, -0.15), new THREE.Vector3(0.4, 0.01, -0.65),
    new THREE.Vector3(0.8, 0.01, -0.35), new THREE.Vector3(1.2, 0.01, -0.7),
  ], GREEN_BRIGHT))
  // Bars
  const bx = [-0.7, -0.2, 0.3, 0.8]
  const bh = [0.3, 0.5, 0.35, 0.55]
  for (let i = 0; i < bx.length; i++) {
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.005, bh[i]),
      new THREE.MeshBasicMaterial({ color: i % 2 ? GREEN : FAINT, transparent: true, opacity: 0.6 }),
    )
    bar.position.set(bx[i], 0.005, 0.4 + bh[i] / 2)
    ag.add(bar)
  }
  const metric = makeLabel('2.4K', 0.13, '#6366f1', true)
  metric.position.set(1.0, 0.1, -1.0)
  ag.add(metric)
  group.add(ag)

  // Workflows — node graph + ACTION button
  const wg = new THREE.Group()
  wg.position.set(0, 0.2, 0)
  wg.rotation.x = -0.06
  const wNodes: [number, number][] = [[-0.8, -0.3], [0, -0.6], [0.7, -0.2], [0.5, 0.4], [-0.3, 0.4]]
  for (const [nx, nz] of wNodes) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.08, 0.11, 16),
      new THREE.MeshBasicMaterial({ color: EDGE, side: THREE.DoubleSide }),
    )
    ring.rotation.x = -Math.PI / 2
    ring.position.set(nx, 0.01, nz)
    wg.add(ring)
  }
  const wEdges = [[0,1],[1,2],[2,3],[3,4],[4,0]]
  for (const [a, b] of wEdges) {
    wg.add(drawLine([
      new THREE.Vector3(wNodes[a][0], 0.01, wNodes[a][1]),
      new THREE.Vector3(wNodes[b][0], 0.01, wNodes[b][1]),
    ], EDGE_LIGHT))
  }
  // ACTION button
  const btn = new THREE.Mesh(
    new THREE.BoxGeometry(0.9, 0.08, 0.28),
    new THREE.MeshStandardMaterial({ color: GREEN, metalness: 0.05, roughness: 0.5 }),
  )
  addEdges(btn, GREEN_DARK)
  btn.position.set(0, 0.06, 0.85)
  btn.userData = { id: 'action:btn', type: 'platform', label: 'ACTION' }
  ctx.interactables.set('action:btn', btn)
  wg.add(btn)
  const btnLbl = makeLabel('ACTION', 0.11, '#ffffff', true)
  btnLbl.position.set(0, 0.14, 0.85)
  wg.add(btnLbl)
  group.add(wg)

  // Integrations — code lines + API dots
  const ig = new THREE.Group()
  ig.position.set(4.6, 0.2, 0)
  ig.rotation.x = -0.06
  for (let i = 0; i < 5; i++) {
    const w = 0.8 + Math.sin(i * 1.7) * 0.6
    ig.add(drawLine([
      new THREE.Vector3(-1.2, 0.01, -0.5 + i * 0.22),
      new THREE.Vector3(-1.2 + w, 0.01, -0.5 + i * 0.22),
    ], i === 2 ? GREEN : EDGE_LIGHT))
  }
  const dots = [[-0.4], [0.1], [0.6]]
  for (let i = 0; i < 3; i++) {
    const dot = new THREE.Mesh(
      new THREE.CircleGeometry(0.06, 12),
      new THREE.MeshBasicMaterial({ color: GREEN, side: THREE.DoubleSide }),
    )
    dot.rotation.x = -Math.PI / 2
    dot.position.set(0.9, 0.01, -0.4 + i * 0.4)
    ig.add(dot)
    ig.add(drawLine([
      new THREE.Vector3(0.4, 0.01, -0.4 + i * 0.4),
      new THREE.Vector3(0.82, 0.01, -0.4 + i * 0.4),
    ], EDGE_LIGHT))
  }
  const apiLbl = makeLabel('REST · gRPC', 0.1, '#71717a')
  apiLbl.position.set(0.4, 0.1, 0.8)
  ig.add(apiLbl)
  group.add(ig)

  ctx.scene.add(group)
}

// ── Middle Layer (y=1.8): Ontology network ──

interface NodeDef { id: string; label: string; x: number; z: number; green: boolean }

const nodes: NodeDef[] = [
  { id: 'node:user', label: 'User', x: 0, z: 0, green: true },
  { id: 'node:contract', label: 'Contract', x: -2.8, z: -1.4, green: false },
  { id: 'node:billing', label: 'Billing', x: -1.8, z: 1.6, green: false },
  { id: 'node:portability', label: 'Portability', x: 2.8, z: -1.6, green: true },
  { id: 'node:voice', label: 'Voice Calls', x: 2.2, z: 1.2, green: false },
  { id: 'node:retention', label: 'Retention', x: -3.2, z: 0.6, green: true },
  { id: 'node:complaint', label: 'Complaints', x: 3.6, z: 0, green: false },
  { id: 'node:arrears', label: 'Arrears', x: 1.2, z: -2.2, green: false },
  { id: 'node:convergence', label: 'Convergence', x: -1.2, z: -2.2, green: true },
]

const edges: [number, number, string][] = [
  [0,1,'Binds'], [0,2,'Bills'], [0,3,'Queries'], [0,4,'Calls'],
  [0,5,'Retains'], [0,6,'Complains'], [0,7,'Owes'], [0,8,'Converges'],
  [1,3,'Restricts'], [7,3,'Blocks'], [6,5,'Influences'],
]

function makePill(label: string, isGreen: boolean): THREE.Group {
  const g = new THREE.Group()
  const pw = Math.max(label.length * 0.12 + 0.3, 0.7)
  const color = isGreen ? GREEN : WARM_WHITE
  const capsule = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.16, pw, 8, 16),
    new THREE.MeshPhysicalMaterial({
      color, metalness: 0, roughness: 0.3,
      transparent: true, opacity: isGreen ? 0.88 : 0.92, clearcoat: 0.05,
    }),
  )
  capsule.rotation.z = Math.PI / 2
  capsule.position.y = 0.16
  g.add(capsule)
  const edgesSeg = new THREE.LineSegments(
    new THREE.EdgesGeometry(capsule.geometry, 15),
    edgeMat(isGreen ? GREEN_DARK : EDGE_LIGHT),
  )
  edgesSeg.rotation.z = Math.PI / 2
  edgesSeg.position.y = 0.16
  g.add(edgesSeg)
  const lbl = makeLabel(label, 0.14, isGreen ? '#ffffff' : '#1a1a1a', true)
  lbl.position.set(0, 0.36, 0)
  g.add(lbl)
  return g
}

function buildMiddleLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = 1.8

  // Main platform — largest, thicker
  const plat = makePlatform(12, 0.25, 7.5, 0.9)
  const box = plat.children[0] as THREE.Mesh
  box.userData = { id: 'platform:ontology', type: 'platform', label: 'ONTOLOGY' }
  ctx.interactables.set('platform:ontology', box)
  group.add(plat)

  // Title
  const title = makeLabel('ONTOLOGY', 0.26, '#52525b', true)
  title.position.set(0, 0.55, -3.5)
  group.add(title)

  // Edges (connections)
  for (const [ai, bi, eLbl] of edges) {
    const a = nodes[ai], b = nodes[bi]
    group.add(drawLine([
      new THREE.Vector3(a.x, 0.15, a.z),
      new THREE.Vector3(b.x, 0.15, b.z),
    ], EDGE_LIGHT))
    const lbl = makeLabel(eLbl, 0.08, '#a1a1aa')
    lbl.position.set((a.x + b.x) / 2, 0.28, (a.z + b.z) / 2)
    group.add(lbl)
  }

  // Nodes
  for (const n of nodes) {
    const pill = makePill(n.label, n.green)
    pill.position.set(n.x, 0.14, n.z)
    pill.userData = { id: n.id, type: 'capsule', label: n.label }
    ctx.interactables.set(n.id, pill)
    group.add(pill)
  }

  ctx.scene.add(group)
}

// ── Bottom Layer (y=-2.5) ──

function buildBottomLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = -2.5

  // DATA platform
  const dp = makePlatform(4.8, 0.22, 3.4)
  dp.position.set(-3.2, 0, 0)
  const dBox = dp.children[0] as THREE.Mesh
  dBox.userData = { id: 'platform:data', type: 'platform', label: 'DATA' }
  ctx.interactables.set('platform:data', dBox)
  group.add(dp)

  const dTitle = makeLabel('DATA', 0.22, '#1a1a1a', true)
  dTitle.position.set(-3.2, 0.4, -1.5)
  group.add(dTitle)

  // Database cylinders (wireframe style)
  for (let i = 0; i < 3; i++) {
    const x = -3.2 + (i - 1) * 1.2
    const cylGeo = new THREE.CylinderGeometry(0.26, 0.26, 0.4, 16)
    const cyl = new THREE.Mesh(cylGeo, new THREE.MeshPhysicalMaterial({
      color: WARM_WHITE, transparent: true, opacity: 0.5, roughness: 0.2, metalness: 0,
    }))
    cyl.position.set(x, 0.32, -0.2)
    group.add(cyl)
    const cylE = new THREE.LineSegments(new THREE.EdgesGeometry(cylGeo), edgeMat(EDGE_LIGHT))
    cylE.position.copy(cyl.position)
    group.add(cylE)
    const lbl = makeLabel(['SQL', 'NoSQL', 'Lake'][i], 0.08, '#71717a', true)
    lbl.position.set(x, 0.6, -0.2)
    group.add(lbl)
  }

  // Table rows
  for (let r = 0; r < 3; r++) {
    const y = 0.14
    const z = 0.5 + r * 0.3
    group.add(drawLine([
      new THREE.Vector3(-4.2, y, z), new THREE.Vector3(-2.2, y, z),
    ], r === 0 ? EDGE_LIGHT : FAINT))
  }

  // MODELS platform
  const mp = makePlatform(4.8, 0.22, 3.4)
  mp.position.set(3.2, 0, 0)
  const mBox = mp.children[0] as THREE.Mesh
  mBox.userData = { id: 'platform:models', type: 'platform', label: 'MODELS' }
  ctx.interactables.set('platform:models', mBox)
  group.add(mp)

  const mTitle = makeLabel('MODELS', 0.22, '#1a1a1a', true)
  mTitle.position.set(3.2, 0.4, -1.5)
  group.add(mTitle)

  // Gear (torus)
  const torusGeo = new THREE.TorusGeometry(0.3, 0.06, 8, 6)
  const torus = new THREE.Mesh(torusGeo, new THREE.MeshPhysicalMaterial({
    color: WARM_WHITE, transparent: true, opacity: 0.5, roughness: 0.2, metalness: 0,
  }))
  torus.position.set(2.4, 0.32, -0.2)
  group.add(torus)
  group.add(new THREE.LineSegments(new THREE.EdgesGeometry(torusGeo), edgeMat(EDGE_LIGHT)).translateX(2.4).translateY(0.32).translateZ(-0.2))
  const gLbl = makeLabel('ML Engine', 0.08, '#71717a', true)
  gLbl.position.set(2.4, 0.6, -0.2)
  group.add(gLbl)

  // Octahedron
  const octGeo = new THREE.OctahedronGeometry(0.25)
  const oct = new THREE.Mesh(octGeo, new THREE.MeshPhysicalMaterial({
    color: WARM_WHITE, transparent: true, opacity: 0.5, roughness: 0.2, metalness: 0,
  }))
  oct.position.set(4.0, 0.32, -0.2)
  group.add(oct)
  group.add(new THREE.LineSegments(new THREE.EdgesGeometry(octGeo), edgeMat(EDGE_LIGHT)).translateX(4.0).translateY(0.32).translateZ(-0.2))
  const nLbl = makeLabel('Neural Net', 0.08, '#71717a', true)
  nLbl.position.set(4.0, 0.6, -0.2)
  group.add(nLbl)

  // Icosahedron
  const icoGeo = new THREE.IcosahedronGeometry(0.2)
  const ico = new THREE.Mesh(icoGeo, new THREE.MeshPhysicalMaterial({
    color: WARM_WHITE, transparent: true, opacity: 0.5, roughness: 0.2, metalness: 0,
  }))
  ico.position.set(3.2, 0.32, 0.7)
  group.add(ico)
  group.add(new THREE.LineSegments(new THREE.EdgesGeometry(icoGeo), edgeMat(EDGE_LIGHT)).translateX(3.2).translateY(0.32).translateZ(0.7))
  const aLbl = makeLabel('Algorithm', 0.08, '#71717a', true)
  aLbl.position.set(3.2, 0.6, 0.7)
  group.add(aLbl)

  ctx.scene.add(group)
}

// ── Flow lines: controlled bundles with smooth curves ──

function buildFlowLines(ctx: ThreeContext) {
  const particleMat = new THREE.MeshBasicMaterial({ color: GREEN_BRIGHT })
  const particleGeo = new THREE.SphereGeometry(0.045, 8, 8)
  const lines: THREE.Line[] = []
  const particles: THREE.Mesh[] = []
  const curves: Array<{ curve: THREE.QuadraticBezierCurve3; t: number }> = []

  function addCurve(s: THREE.Vector3, m: THREE.Vector3, e: THREE.Vector3, withParticle: boolean) {
    const curve = new THREE.QuadraticBezierCurve3(s, m, e)
    const pts = curve.getPoints(48)
    const geo = new THREE.BufferGeometry().setFromPoints(pts)
    const pos = geo.attributes.position
    const dist = new Float32Array(pos.count)
    for (let j = 1; j < pos.count; j++) {
      const dx = pos.getX(j) - pos.getX(j-1)
      const dy = pos.getY(j) - pos.getY(j-1)
      const dz = pos.getZ(j) - pos.getZ(j-1)
      dist[j] = dist[j-1] + Math.sqrt(dx*dx + dy*dy + dz*dz)
    }
    geo.setAttribute('lineDistance', new THREE.BufferAttribute(dist, 1))
    const mat = new THREE.LineDashedMaterial({
      color: EDGE_LIGHT, dashSize: 0.18, gapSize: 0.12, transparent: true, opacity: 0.35,
    })
    const line = new THREE.Line(geo, mat)
    ctx.scene.add(line)
    lines.push(line)
    if (withParticle) {
      const p = new THREE.Mesh(particleGeo, particleMat)
      p.position.copy(curve.getPoint(0))
      ctx.scene.add(p)
      particles.push(p)
      curves.push({ curve, t: Math.random() })
    }
  }

  // Bottom → Middle: converging bundle
  const bY = -2.2, mY = 1.65
  for (let i = 0; i < 14; i++) {
    const t = i / 13
    const xS = -4.5 + t * 9 + (Math.random() - 0.5) * 0.6
    const zS = (Math.random() - 0.5) * 2
    // Converge toward center of middle layer
    const xE = (Math.random() - 0.5) * 5
    const zE = (Math.random() - 0.5) * 3.5
    const xM = (xS + xE) / 2 + (Math.random() - 0.5) * 1.5
    const zM = (zS + zE) / 2 + (Math.random() - 0.5) * 1
    addCurve(
      new THREE.Vector3(xS, bY, zS),
      new THREE.Vector3(xM, (bY + mY) / 2, zM),
      new THREE.Vector3(xE, mY, zE),
      i < 10,
    )
  }

  // Middle → Top: fanning out to 3 panels
  const tY = 5.35
  const px = [-4.6, 0, 4.6]
  for (let i = 0; i < 14; i++) {
    const xS = (Math.random() - 0.5) * 5
    const zS = (Math.random() - 0.5) * 3.5
    const target = px[i % 3]
    const xE = target + (Math.random() - 0.5) * 1.8
    const zE = (Math.random() - 0.5) * 1.2
    const xM = (xS + xE) / 2 + (Math.random() - 0.5) * 1.2
    const zM = (zS + zE) / 2 + (Math.random() - 0.5) * 0.8
    addCurve(
      new THREE.Vector3(xS, mY + 0.2, zS),
      new THREE.Vector3(xM, (mY + tY) / 2, zM),
      new THREE.Vector3(xE, tY, zE),
      i < 10,
    )
  }

  ctx.animationCallbacks.push(() => {
    const speed = 0.0025
    for (const line of lines) {
      (line.material as THREE.LineDashedMaterial).dashOffset -= speed * 5
    }
    for (let i = 0; i < curves.length; i++) {
      curves[i].t = (curves[i].t + speed) % 1
      curves[i].curve.getPoint(curves[i].t, particles[i].position)
    }
  })
}

// ── Public API ──

export function buildIsometricScene(ctx: ThreeContext) {
  buildBottomLayer(ctx)
  buildMiddleLayer(ctx)
  buildTopLayer(ctx)
  buildFlowLines(ctx)
}
