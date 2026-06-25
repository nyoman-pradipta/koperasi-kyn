<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['submit', 'cancel'])

const form = reactive({
  full_name: '',
  nik: '',
  phone: '',
  email: '',
  address: '',
  join_date: '',
  status: 'aktif',
})

// isi ulang form ketika modelValue berubah (mode edit)
watch(
  () => props.modelValue,
  (val) => {
    Object.assign(form, {
      full_name: val.full_name || '',
      nik: val.nik || '',
      phone: val.phone || '',
      email: val.email || '',
      address: val.address || '',
      join_date: val.join_date || '',
      status: val.status || 'aktif',
    })
  },
  { immediate: true, deep: true }
)

function submit() {
  // buang field kosong agar tidak menimpa dengan string kosong
  const payload = {}
  for (const [k, v] of Object.entries(form)) {
    if (v !== '') payload[k] = v
  }
  emit('submit', payload)
}
</script>

<template>
  <form @submit.prevent="submit" class="form">
    <label>
      Nama Lengkap *
      <input v-model="form.full_name" required />
    </label>
    <div class="row">
      <label>
        NIK (KTP)
        <input v-model="form.nik" />
      </label>
      <label>
        No. HP
        <input v-model="form.phone" />
      </label>
    </div>
    <label>
      Email
      <input v-model="form.email" type="email" />
    </label>
    <label>
      Alamat
      <textarea v-model="form.address" rows="2" />
    </label>
    <div class="row">
      <label>
        Tanggal Masuk
        <input v-model="form.join_date" type="date" />
      </label>
      <label>
        Status
        <select v-model="form.status">
          <option value="aktif">Aktif</option>
          <option value="nonaktif">Nonaktif</option>
        </select>
      </label>
    </div>

    <div class="actions">
      <button type="button" class="btn ghost" @click="$emit('cancel')">Batal</button>
      <button type="submit" class="btn">Simpan</button>
    </div>
  </form>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

label {
  display: block;
  font-size: 0.82rem;
  color: var(--muted);
}

input,
select,
textarea {
  width: 100%;
  margin-top: 4px;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.92rem;
  font-family: inherit;
}

input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.btn {
  padding: 10px 18px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn:hover {
  background: var(--primary-dark);
}

.btn.ghost {
  background: #fff;
  color: var(--text);
  border: 1px solid var(--border);
}
</style>
