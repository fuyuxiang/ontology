import * as THREE from 'three'
import { ref, type Ref } from 'vue'
import type { ThreeContext } from './useThreeScene'

export interface SceneSelection {
  id: string
  type: string
  label: string
  color: string
  positionY: number
}

export interface SceneInteraction {
  selectedId: Ref<string | null>
  selectedData: Ref<SceneSelection | null>
  attach: (ctx: ThreeContext) => void
  detach: () => void
  applyOverride: (field: string, value: string | number) => void
}

const DEFAULT_EDGE = 0x1a1a1a
const HIGHLIGHT_EDGE = 0x6366f1
const HOVER_EDGE = 0x818cf8

function setEdgeColor(obj: THREE.Object3D, color: number) {
  obj.traverse((child) => {
    if (child instanceof THREE.LineSegments) {
      const mat = child.material as THREE.LineBasicMaterial
      mat.color.setHex(color)
    }
  })
}

function getMainMaterial(obj: THREE.Object3D): THREE.MeshStandardMaterial | null {
  let found: THREE.MeshStandardMaterial | null = null
  obj.traverse((child) => {
    if (!found && child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
      found = child.material
    }
  })
  return found
}

export function createSceneInteraction(): SceneInteraction {
  const selectedId = ref<string | null>(null)
  const selectedData = ref<SceneSelection | null>(null)

  let context: ThreeContext | null = null
  const raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  let currentHoverId: string | null = null
  let canvas: HTMLCanvasElement | null = null

  function findHit(event: MouseEvent): { id: string; obj: THREE.Object3D } | null {
    if (!context || !canvas) return null
    const rect = canvas.getBoundingClientRect()
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
    raycaster.setFromCamera(pointer, context.camera)

    const allObjects: THREE.Object3D[] = []
    for (const obj of context.interactables.values()) {
      obj.traverse((c) => { if (c instanceof THREE.Mesh) allObjects.push(c) })
    }

    const intersects = raycaster.intersectObjects(allObjects, false)
    if (intersects.length === 0) return null

    // Walk up to find the interactable parent
    let hit = intersects[0].object
    while (hit && !hit.userData?.id) {
      hit = hit.parent!
    }
    if (!hit?.userData?.id) return null
    return { id: hit.userData.id, obj: hit }
  }

  function onPointerMove(event: MouseEvent) {
    const hit = findHit(event)
    const newId = hit?.id ?? null

    if (newId === currentHoverId) return

    // Unhover previous
    if (currentHoverId && currentHoverId !== selectedId.value && context) {
      const prev = context.interactables.get(currentHoverId)
      if (prev) setEdgeColor(prev, DEFAULT_EDGE)
    }

    // Hover new
    if (newId && newId !== selectedId.value && context) {
      const obj = context.interactables.get(newId)
      if (obj) setEdgeColor(obj, HOVER_EDGE)
    }

    currentHoverId = newId
    if (canvas) canvas.style.cursor = newId ? 'pointer' : 'default'
  }

  function onClick(event: MouseEvent) {
    if (!context) return
    const hit = findHit(event)

    // Deselect previous
    if (selectedId.value) {
      const prev = context.interactables.get(selectedId.value)
      if (prev) setEdgeColor(prev, DEFAULT_EDGE)
    }

    if (!hit) {
      selectedId.value = null
      selectedData.value = null
      return
    }

    // Select new
    selectedId.value = hit.id
    const obj = context.interactables.get(hit.id)!
    setEdgeColor(obj, HIGHLIGHT_EDGE)

    const mat = getMainMaterial(obj)
    selectedData.value = {
      id: hit.id,
      type: obj.userData.type ?? 'unknown',
      label: obj.userData.label ?? hit.id,
      color: mat ? '#' + mat.color.getHexString() : '#ffffff',
      positionY: obj.position.y,
    }
  }

  function attach(ctx: ThreeContext) {
    context = ctx
    canvas = ctx.renderer.domElement
    canvas.addEventListener('pointermove', onPointerMove)
    canvas.addEventListener('click', onClick)
  }

  function detach() {
    if (canvas) {
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('click', onClick)
    }
    context = null
    canvas = null
  }

  function applyOverride(field: string, value: string | number) {
    if (!context || !selectedId.value) return
    const obj = context.interactables.get(selectedId.value)
    if (!obj) return

    if (field === 'color' && typeof value === 'string') {
      obj.traverse((child) => {
        if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
          child.material.color.set(value)
        }
      })
      if (selectedData.value) selectedData.value.color = value
    } else if (field === 'label' && typeof value === 'string') {
      obj.userData.label = value
      if (selectedData.value) selectedData.value.label = value

      // Update sprite text in 3D scene
      if (obj instanceof THREE.Group || obj instanceof THREE.Object3D) {
        const oldSprite = obj.children.find(c => c instanceof THREE.Sprite) as THREE.Sprite | undefined
        if (oldSprite) {
          // Recreate sprite with new text
          const canvas = document.createElement('canvas')
          const scale = 4
          const ctxC = canvas.getContext('2d')!
          const fontSize = Math.round(0.16 * 100 * scale)
          ctxC.font = `700 ${fontSize}px Inter, system-ui, sans-serif`
          const metrics = ctxC.measureText(value)
          canvas.width = Math.ceil(metrics.width) + 8 * scale
          canvas.height = fontSize * 1.4
          ctxC.font = `700 ${fontSize}px Inter, system-ui, sans-serif`
          ctxC.fillStyle = '#1a1a1a'
          ctxC.textBaseline = 'middle'
          ctxC.fillText(value, 4 * scale, canvas.height / 2)

          const tex = new THREE.CanvasTexture(canvas)
          tex.minFilter = THREE.LinearFilter
          oldSprite.material.map?.dispose()
          oldSprite.material.map = tex
          oldSprite.material.needsUpdate = true
          const aspect = canvas.width / canvas.height
          oldSprite.scale.set(0.16 * aspect, 0.16, 1)
        }
      }
    } else if (field === 'positionY' && typeof value === 'number') {
      obj.position.y = value
      if (selectedData.value) selectedData.value.positionY = value
    }
  }

  return { selectedId, selectedData, attach, detach, applyOverride }
}
