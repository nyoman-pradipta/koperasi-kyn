<script setup>
defineProps({
  title: { type: String, default: '' },
  show: { type: Boolean, default: false },
})
defineEmits(['close'])
</script>

<template>
  <transition name="modal">
    <div v-if="show" class="overlay" @click.self="$emit('close')">
      <div class="modal">
        <header class="modal-head">
          <h3>{{ title }}</h3>
          <button class="x" @click="$emit('close')">×</button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal-foot">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 16px;
  z-index: 50;
}

.modal {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 520px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-head h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--primary-dark);
}

.x {
  border: none;
  background: none;
  font-size: 1.4rem;
  cursor: pointer;
  color: var(--muted);
  line-height: 1;
}

.modal-body {
  padding: 20px;
}

.modal-foot {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
