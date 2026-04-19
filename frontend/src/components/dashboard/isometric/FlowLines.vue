<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

let groupObj: THREE.Group | null = null
const lines: THREE.Line[] = []
const particles: THREE.Mesh[] = []
const curveData: Array<{ curve: THREE.QuadraticBezierCurve3; t: number }> = []

let rafId = 0

function onGroupReady(instance: any) {
  // TresJS passes the Three.js object as the template ref
  if (instance && instance instanceof THREE.Group) {
    groupObj = instance
    createScene()
    animate()
  }
}

function createScene() {
  if (!groupObj) return

  const particleMat = new THREE.MeshBasicMaterial({ color: 0x4ade80 })
  const particleGeo = new THREE.SphereGeometry(0.06, 8, 8)

  // Bottom → Middle (5 lines)
  for (let i = 0; i < 5; i++) {
    const xStart = -3 + i * 1.5
    const xEnd = xStart + (Math.random() - 0.5) * 1.5
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(xStart, -1.8, (Math.random() - 0.5) * 2),
      new THREE.Vector3((xStart + xEnd) / 2, 0, (Math.random() - 0.5) * 1.5),
      new THREE.Vector3(xEnd, 1.9, (Math.random() - 0.5) * 2),
    )
    addFlowLine(groupObj, curve, particleMat, particleGeo)
  }

  // Middle → Top (5 lines)
  for (let i = 0; i < 5; i++) {
    const xStart = -3 + i * 1.5 + (Math.random() - 0.5)
    const xEnd = -4 + i * 2
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(xStart, 2.2, (Math.random() - 0.5) * 2),
      new THREE.Vector3((xStart + xEnd) / 2, 4, (Math.random() - 0.5) * 1.5),
      new THREE.Vector3(xEnd, 5.8, (Math.random() - 0.5) * 1),
    )
    addFlowLine(groupObj, curve, particleMat, particleGeo)
  }
}

function addFlowLine(
  group: THREE.Group,
  curve: THREE.QuadraticBezierCurve3,
  particleMat: THREE.Material,
  particleGeo: THREE.BufferGeometry,
) {
  const points = curve.getPoints(40)
  const geo = new THREE.BufferGeometry().setFromPoints(points)

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
    color: 0x1a1a1a,
    dashSize: 0.3,
    gapSize: 0.2,
  })

  const line = new THREE.Line(geo, mat)
  group.add(line)
  lines.push(line)

  const particle = new THREE.Mesh(particleGeo, particleMat)
  const startPoint = curve.getPoint(0)
  particle.position.copy(startPoint)
  group.add(particle)
  particles.push(particle)
  curveData.push({ curve, t: Math.random() })
}

function animate() {
  const speed = 0.004

  for (const line of lines) {
    const mat = line.material as THREE.LineDashedMaterial
    mat.dashOffset -= speed * 8
  }

  for (let i = 0; i < curveData.length; i++) {
    const data = curveData[i]
    data.t = (data.t + speed) % 1
    data.curve.getPoint(data.t, particles[i].position)
  }

  rafId = requestAnimationFrame(animate)
}

onUnmounted(() => {
  cancelAnimationFrame(rafId)
  for (const line of lines) {
    line.geometry.dispose()
    ;(line.material as THREE.Material).dispose()
  }
})
</script>

<template>
  <TresGroup @ready="onGroupReady" />
</template>
