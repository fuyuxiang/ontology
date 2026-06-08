<template>
  <div class="pg-menubar" @click.stop>
    <div class="pg-menubar__item" @click="toggleFile">
      文件
      <div v-if="fileMenuOpen" class="pg-menu-dropdown">
        <div class="pg-menu-item" @click.stop="emit('new'); closeAll()">新建本体</div>
        <div class="pg-menu-item" @click.stop="emit('open'); closeAll()">打开...</div>
        <div class="pg-menu-sep"></div>
        <div class="pg-menu-item" @click.stop="store.saveDraft(); closeAll()">保存草稿</div>
        <div class="pg-menu-item" @click.stop="emit('save'); closeAll()">导出为 OWL/XML...</div>
      </div>
    </div>
    <div class="pg-menubar__item" @click="toggleEdit">
      编辑
      <div v-if="editMenuOpen" class="pg-menu-dropdown">
        <div class="pg-menu-item" @click.stop="store.undo(); closeAll()">撤销</div>
        <div class="pg-menu-item" @click.stop="store.redo(); closeAll()">重做</div>
      </div>
    </div>
    <div style="flex:1"></div>
    <div class="pg-menubar__status" v-if="store.isDirty">● 已修改</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useOwlEditorStore } from '../../../../store/owlEditor'

const store = useOwlEditorStore()
const emit = defineEmits<{ (e: 'new'): void; (e: 'open'): void; (e: 'save'): void }>()

const fileMenuOpen = ref(false)
const editMenuOpen = ref(false)

function toggleFile() {
  fileMenuOpen.value = !fileMenuOpen.value
  editMenuOpen.value = false
}

function toggleEdit() {
  editMenuOpen.value = !editMenuOpen.value
  fileMenuOpen.value = false
}

function closeAll() {
  fileMenuOpen.value = false
  editMenuOpen.value = false
}

function closeMenus() {
  closeAll()
}

onMounted(() => document.addEventListener('click', closeMenus))
onBeforeUnmount(() => document.removeEventListener('click', closeMenus))
</script>

<style scoped>
.pg-menubar { position: relative; }
.pg-menubar__item { position: relative; }
.pg-menubar__status { font-size: 11px; color: #c55; padding-right: 8px; }
.pg-menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 100;
  background: #fff;
  border: 1px solid var(--pg-border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  min-width: 160px;
  padding: 2px 0;
}
.pg-menu-item {
  padding: 4px 16px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.pg-menu-item:hover {
  background: var(--pg-select-bg);
  color: var(--pg-select-text);
}
.pg-menu-sep {
  height: 1px;
  background: var(--pg-border-light);
  margin: 2px 0;
}
</style>
