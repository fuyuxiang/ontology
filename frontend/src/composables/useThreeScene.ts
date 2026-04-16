import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export interface ThreeContext {
  scene: THREE.Scene
  camera: THREE.OrthographicCamera
  renderer: THREE.WebGLRenderer
  controls: OrbitControls
  interactables: Map<string, THREE.Object3D>
  animationCallbacks: Array<(dt: number) => void>
  dispose: () => void
}

export function createThreeScene(container: HTMLElement): ThreeContext {
  const w = container.clientWidth
  const h = container.clientHeight
  const aspect = w / h

  // Scene
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf1f5f9)

  // Orthographic camera — isometric view, tighter framing
  const frustum = 10
  const camera = new THREE.OrthographicCamera(
    -frustum * aspect, frustum * aspect,
    frustum, -frustum,
    0.1, 200,
  )
  camera.position.set(14, 12, 14)
  camera.lookAt(0, 1.5, 0)
  camera.zoom = 1.3
  camera.updateProjectionMatrix()

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  container.appendChild(renderer.domElement)

  // Lighting — soft, even illumination
  const ambient = new THREE.AmbientLight(0xffffff, 0.85)
  scene.add(ambient)

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.6)
  dirLight1.position.set(10, 20, 12)
  scene.add(dirLight1)

  const dirLight2 = new THREE.DirectionalLight(0xeef0ff, 0.25)
  dirLight2.position.set(-8, 10, -6)
  scene.add(dirLight2)

  // Subtle hemisphere light for fill
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe0e0e0, 0.3)
  scene.add(hemiLight)

  // Orbit controls
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minPolarAngle = 0.4
  controls.maxPolarAngle = 1.2
  controls.minAzimuthAngle = -0.8
  controls.maxAzimuthAngle = 0.8
  controls.enableZoom = true
  controls.enablePan = true

  // Storage
  const interactables = new Map<string, THREE.Object3D>()
  const animationCallbacks: Array<(dt: number) => void> = []

  // Animation loop
  const clock = new THREE.Clock()
  let rafId = 0

  function animate() {
    rafId = requestAnimationFrame(animate)
    const dt = clock.getDelta()
    controls.update()
    for (const cb of animationCallbacks) cb(dt)
    renderer.render(scene, camera)
  }
  animate()

  // Resize
  function onResize() {
    const nw = container.clientWidth
    const nh = container.clientHeight
    const na = nw / nh
    camera.left = -frustum * na
    camera.right = frustum * na
    camera.top = frustum
    camera.bottom = -frustum
    camera.updateProjectionMatrix()
    renderer.setSize(nw, nh)
  }

  const ro = new ResizeObserver(onResize)
  ro.observe(container)

  function dispose() {
    cancelAnimationFrame(rafId)
    ro.disconnect()
    controls.dispose()
    renderer.dispose()
    renderer.domElement.remove()
  }

  return { scene, camera, renderer, controls, interactables, animationCallbacks, dispose }
}
