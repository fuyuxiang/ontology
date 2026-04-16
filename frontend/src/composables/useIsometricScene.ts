import * as THREE from 'three'
import type { ThreeContext } from './useThreeScene'

const WHITE = 0xffffff
const EDGE_COLOR = 0x1a1a1a
const GREEN = 0x4ade80
const GREEN_DARK = 0x166534
const LIGHT_GRAY = 0xf5f5f5

// ── Helpers ──

function addEdges(mesh: THREE.Mesh, color = EDGE_COLOR) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 15)
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color }))
  mesh.add(line)
  return line
}

function makeBox(w: number, h: number, d: number, color = WHITE): THREE.Mesh {
  const geo = new THREE.BoxGeometry(w, h, d)
  const mat = new THREE.MeshStandardMaterial({ color, metalness: 0.05, roughness: 0.9 })
  const mesh = new THREE.Mesh(geo, mat)
  addEdges(mesh)
  return mesh
}

function makeCylinder(rTop: number, rBot: number, h: number, segs = 16, color = WHITE): THREE.Mesh {
  const geo = new THREE.CylinderGeometry(rTop, rBot, h, segs)
  const mat = new THREE.MeshStandardMaterial({ color, metalness: 0.05, roughness: 0.9 })
  const mesh = new THREE.Mesh(geo, mat)
  addEdges(mesh)
  return mesh
}

function makeCapsule(r: number, len: number, color = GREEN): THREE.Mesh {
  const geo = new THREE.CapsuleGeometry(r, len, 8, 16)
  const mat = new THREE.MeshStandardMaterial({ color, metalness: 0.2, roughness: 0.4 })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.rotation.z = Math.PI / 2
  return mesh
}

// ── Top Layer (y=6) ──

function buildTopLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = 6

  const platforms = [
    { id: 'platform:analytics', label: 'ANALYTICS', x: -4.5 },
    { id: 'platform:workflows', label: 'WORKFLOWS', x: 0 },
    { id: 'platform:integrations', label: 'INTEGRATIONS', x: 4.5 },
  ]

  for (const p of platforms) {
    const base = makeBox(3.5, 0.15, 2.5)
    base.position.set(p.x, 0, 0)
    base.userData = { id: p.id, type: 'platform', label: p.label }
    ctx.interactables.set(p.id, base)
    group.add(base)

    // Decorative boxes
    const deco1 = makeBox(0.6, 0.25, 0.4)
    deco1.position.set(p.x - 0.8, 0.2, 0.4)
    group.add(deco1)

    const deco2 = makeBox(0.8, 0.2, 0.5)
    deco2.position.set(p.x + 0.5, 0.2, -0.3)
    group.add(deco2)
  }

  // ACTION button
  const actionGeo = new THREE.BoxGeometry(1.2, 0.2, 0.5)
  const actionMat = new THREE.MeshStandardMaterial({ color: GREEN, metalness: 0.2, roughness: 0.4 })
  const actionBtn = new THREE.Mesh(actionGeo, actionMat)
  addEdges(actionBtn, GREEN_DARK)
  actionBtn.position.set(0, 0.25, 0.6)
  actionBtn.userData = { id: 'action:btn', type: 'platform', label: 'ACTION' }
  ctx.interactables.set('action:btn', actionBtn)
  group.add(actionBtn)

  ctx.scene.add(group)
}

// ── Middle Layer (y=2) ──

const capsuleSlots: [number, number, number][] = [
  [-2.5, 0.25, -1.5], [-0.8, 0.25, -2], [1.2, 0.25, -1.2],
  [2.8, 0.25, -0.3], [-2, 0.25, 0.8], [0, 0.25, 1.5],
  [2, 0.25, 1], [-1, 0.25, 0], [3, 0.25, -2],
]

const capsuleLabels = ['Produces', 'Delivers', 'Carries', 'Monitors', 'Queries', 'Binds', 'Bills', 'Retains', 'Blocks']

const entitySlots: Array<{ pos: [number, number, number]; type: string }> = [
  { pos: [-3.5, 0.35, 0], type: 'factory' },
  { pos: [-1.5, 0.35, -1], type: 'person' },
  { pos: [0.5, 0.35, 0.5], type: 'truck' },
  { pos: [2, 0.35, -1.5], type: 'building' },
  { pos: [3.5, 0.35, 0.8], type: 'person' },
  { pos: [-0.5, 0.35, 2], type: 'building' },
]

function buildEntityMesh(type: string): THREE.Group {
  const g = new THREE.Group()
  if (type === 'factory') {
    const body = makeBox(0.6, 0.4, 0.4, LIGHT_GRAY)
    g.add(body)
    const chimney = makeCylinder(0.06, 0.06, 0.3, 8, LIGHT_GRAY)
    chimney.position.set(0.15, 0.35, 0)
    g.add(chimney)
  } else if (type === 'person') {
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.15, 12, 12),
      new THREE.MeshStandardMaterial({ color: LIGHT_GRAY }),
    )
    addEdges(head, 0x555555)
    head.position.y = 0.15
    g.add(head)
    const body2 = makeCylinder(0.12, 0.15, 0.25, 8, LIGHT_GRAY)
    body2.position.y = -0.05
    g.add(body2)
  } else if (type === 'truck') {
    const cargo = makeBox(0.7, 0.25, 0.3, LIGHT_GRAY)
    g.add(cargo)
    const cab = makeBox(0.2, 0.3, 0.28, LIGHT_GRAY)
    cab.position.set(0.3, 0.05, 0)
    g.add(cab)
  } else {
    const bld = makeBox(0.35, 0.6, 0.35, LIGHT_GRAY)
    g.add(bld)
  }
  return g
}

function buildMiddleLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = 2

  // Main platform
  const platform = makeBox(10, 0.12, 6)
  platform.userData = { id: 'platform:ontology', type: 'platform', label: 'ONTOLOGY' }
  ctx.interactables.set('platform:ontology', platform)
  group.add(platform)

  // Wireframe grid
  const gridGeo = new THREE.PlaneGeometry(9.8, 5.8, 10, 6)
  const gridMat = new THREE.MeshBasicMaterial({ color: 0xe5e5e5, wireframe: true })
  const grid = new THREE.Mesh(gridGeo, gridMat)
  grid.rotation.x = -Math.PI / 2
  grid.position.y = 0.065
  group.add(grid)

  // Capsule nodes
  for (let i = 0; i < capsuleSlots.length; i++) {
    const capsule = makeCapsule(0.15, 0.5)
    capsule.position.set(...capsuleSlots[i])
    const id = `capsule:${i}`
    capsule.userData = { id, type: 'capsule', label: capsuleLabels[i] ?? `Rel ${i}` }
    ctx.interactables.set(id, capsule)
    group.add(capsule)
  }

  // Entity meshes
  for (let i = 0; i < entitySlots.length; i++) {
    const slot = entitySlots[i]
    const entity = buildEntityMesh(slot.type)
    entity.position.set(...slot.pos)
    const id = `entity:${i}`
    entity.userData = { id, type: 'entity', label: slot.type }
    ctx.interactables.set(id, entity)
    group.add(entity)
  }

  ctx.scene.add(group)
}

// ── Bottom Layer (y=-2) ──

function buildBottomLayer(ctx: ThreeContext) {
  const group = new THREE.Group()
  group.position.y = -2

  // DATA platform
  const dataBase = makeBox(4, 0.15, 3)
  dataBase.position.set(-2.5, 0, 0)
  dataBase.userData = { id: 'platform:data', type: 'platform', label: 'DATA' }
  ctx.interactables.set('platform:data', dataBase)
  group.add(dataBase)

  // Database cylinders
  for (let i = 0; i < 3; i++) {
    const cyl = makeCylinder(0.3, 0.3, 0.5, 16)
    cyl.position.set(-2.5 + (-1.2 + i * 1.2), 0.35, 0)
    group.add(cyl)
  }

  // MODELS platform
  const modelsBase = makeBox(4, 0.15, 3)
  modelsBase.position.set(2.5, 0, 0)
  modelsBase.userData = { id: 'platform:models', type: 'platform', label: 'MODELS' }
  ctx.interactables.set('platform:models', modelsBase)
  group.add(modelsBase)

  // Gear torus
  const torusGeo = new THREE.TorusGeometry(0.35, 0.08, 8, 6)
  const torusMat = new THREE.MeshStandardMaterial({ color: WHITE, metalness: 0.1, roughness: 0.8 })
  const torus = new THREE.Mesh(torusGeo, torusMat)
  addEdges(torus)
  torus.position.set(2.5 - 0.6, 0.3, 0)
  group.add(torus)

  // Octahedron
  const octGeo = new THREE.OctahedronGeometry(0.3)
  const octMat = new THREE.MeshStandardMaterial({ color: WHITE, metalness: 0.1, roughness: 0.8 })
  const oct = new THREE.Mesh(octGeo, octMat)
  addEdges(oct)
  oct.position.set(2.5 + 0.6, 0.3, 0)
  group.add(oct)

  ctx.scene.add(group)
}

// ── Flow Lines + Particles ──

function buildFlowLines(ctx: ThreeContext) {
  const particleMat = new THREE.MeshBasicMaterial({ color: GREEN })
  const particleGeo = new THREE.SphereGeometry(0.06, 8, 8)
  const lines: THREE.Line[] = []
  const particles: THREE.Mesh[] = []
  const curves: Array<{ curve: THREE.QuadraticBezierCurve3; t: number }> = []

  function addFlow(
    startY: number, endY: number,
    count: number, xRange: number,
  ) {
    for (let i = 0; i < count; i++) {
      const xStart = -xRange / 2 + i * (xRange / (count - 1))
      const xEnd = xStart + (Math.random() - 0.5) * 1.5
      const midY = (startY + endY) / 2
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(xStart, startY, (Math.random() - 0.5) * 2),
        new THREE.Vector3((xStart + xEnd) / 2, midY, (Math.random() - 0.5) * 1.5),
        new THREE.Vector3(xEnd, endY, (Math.random() - 0.5) * 2),
      )

      const points = curve.getPoints(40)
      const geo = new THREE.BufferGeometry().setFromPoints(points)

      // Compute line distances for dashed material
      const positions = geo.attributes.position
      const distances = new Float32Array(positions.count)
      for (let j = 1; j < positions.count; j++) {
        const dx = positions.getX(j) - positions.getX(j - 1)
        const dy = positions.getY(j) - positions.getY(j - 1)
        const dz = positions.getZ(j) - positions.getZ(j - 1)
        distances[j] = distances[j - 1] + Math.sqrt(dx * dx + dy * dy + dz * dz)
      }
      geo.setAttribute('lineDistance', new THREE.BufferAttribute(distances, 1))

      const mat = new THREE.LineDashedMaterial({
        color: EDGE_COLOR,
        dashSize: 0.3,
        gapSize: 0.2,
      })

      const line = new THREE.Line(geo, mat)
      ctx.scene.add(line)
      lines.push(line)

      const particle = new THREE.Mesh(particleGeo, particleMat)
      particle.position.copy(curve.getPoint(0))
      ctx.scene.add(particle)
      particles.push(particle)
      curves.push({ curve, t: Math.random() })
    }
  }

  // Bottom → Middle
  addFlow(-1.8, 1.9, 5, 6)
  // Middle → Top
  addFlow(2.2, 5.8, 5, 6)

  // Animation callback
  ctx.animationCallbacks.push((_dt: number) => {
    const speed = 0.004
    for (const line of lines) {
      const mat = line.material as THREE.LineDashedMaterial
      mat.dashOffset -= speed * 8
    }
    for (let i = 0; i < curves.length; i++) {
      const data = curves[i]
      data.t = (data.t + speed) % 1
      data.curve.getPoint(data.t, particles[i].position)
    }
  })
}

// ── Public API ──

export function buildIsometricScene(ctx: ThreeContext) {
  buildTopLayer(ctx)
  buildMiddleLayer(ctx)
  buildBottomLayer(ctx)
  buildFlowLines(ctx)
}
