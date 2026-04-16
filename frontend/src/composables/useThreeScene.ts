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
  scene.background = new THREE.Color(0xf4f4f5)

  // Orthographic camera — isometric view
  const frustum = 12
  const camera = new THREE.OrthographicCamera(
    -frustum * aspect, frustum * aspect,
    frustum, -frustum,
    0.1, 100,
  )
  // Isometric angles: ~35° elevation, ~45° azimuth
  camera.position.set(12, 10, 12)
  camera.lookAt(0, 2, 0)
  camera.zoom = 1
  camera.updateProjectionMatrix()

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.appendChild(renderer.domElement)

  // Lighting
  const ambient = new THREE.AmbientLight(0xffffff, 0.7)
  scene.add(ambient)

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8)
  dirLight1.position.set(8, 15, 10)
  dirLight1.castShadow = true
  scene.add(dirLight1)

  const dirLight2 = new THREE.DirectionalLight(0xf0f0ff, 0.3)
  dirLight2.position.set(-5, 8, -5)
  scene.add(dirLight2)

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
