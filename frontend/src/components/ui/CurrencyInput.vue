<!--
  CurrencyInput — Input IDR dengan format ribuan real-time.

  Cara pakai:
    <CurrencyInput v-model="form.amount" placeholder="0" />
    <CurrencyInput v-model="form.form_fee" :min="0" class="..." />

  Nilai yang masuk/keluar melalui v-model selalu berupa Number.
  Tampilan internal menggunakan titik pemisah ribuan (id-ID).
-->
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  placeholder: { type: String, default: '0' },
  min: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  id: { type: String, default: undefined },
  class: { type: String, default: undefined },
})

const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Angka → string dengan titik ribuan: 20000000 → "20.000.000" */
function toDisplay(num) {
  if (!num && num !== 0) return ''
  const n = parseInt(String(num).replace(/\./g, '').replace(/[^0-9]/g, ''), 10)
  if (isNaN(n) || n === 0) return ''
  return n.toLocaleString('id-ID')
}

/** String display → Number bersih: "20.000.000" → 20000000 */
function toRaw(str) {
  const clean = String(str).replace(/\./g, '').replace(/[^0-9]/g, '')
  return clean === '' ? 0 : parseInt(clean, 10)
}

// ── State ────────────────────────────────────────────────────────────────────

// Tampilan teks di dalam input (mengandung titik ribuan)
const display = ref(toDisplay(props.modelValue))

// Sync dari parent (misalnya parent set form.amount = data.suggested_penalty)
watch(
  () => props.modelValue,
  (val) => {
    // Hanya update display jika nilai number-nya memang berbeda
    // (menghindari loop ketika kita yang trigger update:modelValue)
    if (toRaw(display.value) !== val) {
      display.value = toDisplay(val)
    }
  },
)

// ── Event handlers ────────────────────────────────────────────────────────────

function onInput(e) {
  const el = e.target
  const raw = el.value

  // Posisi kursor sebelum format
  const cursorFromEnd = raw.length - (el.selectionEnd ?? raw.length)

  // Hanya angka
  const digits = raw.replace(/[^0-9]/g, '')
  const num = digits === '' ? 0 : parseInt(digits, 10)
  const formatted = digits === '' ? '' : num.toLocaleString('id-ID')

  // Update tampilan tanpa memicu loop
  display.value = formatted
  // Paksa sync DOM (Vue mungkin tidak re-render karena nilai sama)
  el.value = formatted

  // Kembalikan posisi kursor secara proporsional
  const newPos = Math.max(0, formatted.length - cursorFromEnd)
  el.setSelectionRange(newPos, newPos)

  // Emit angka bersih ke parent
  emit('update:modelValue', num)
}

function onFocus(e) {
  // Pilih seluruh isi input saat fokus agar mudah diedit ulang
  e.target.select()
}

function onBlur(e) {
  // Pastikan jika user kosongkan input, model-nya 0
  if (e.target.value === '') {
    display.value = ''
    emit('update:modelValue', 0)
  }
}
</script>

<template>
  <input
    ref="inputRef"
    type="text"
    inputmode="numeric"
    autocomplete="off"
    :id="id"
    :placeholder="placeholder"
    :disabled="disabled"
    :value="display"
    @input="onInput"
    @focus="onFocus"
    @blur="onBlur"
  />
</template>
