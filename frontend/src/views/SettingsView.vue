<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { useUiStore } from '../stores/ui'
import CurrencyInput from '../components/ui/CurrencyInput.vue'

const ui = useUiStore()
const settings = ref({
  coop_name: '',
  coop_address: '',
  printer_size: '58mm',
  late_fee_per_day: '20000',
  shu_cadangan: '25',
  shu_jasa_modal: '20',
  shu_jasa_usaha: '25',
  shu_pengurus: '10',
  shu_dana_sosial: '10',
  shu_pendidikan: '10',
  max_loan_without_collateral: '5000000',
})

const shuTotal = computed(() =>
  ['shu_cadangan', 'shu_jasa_modal', 'shu_jasa_usaha', 'shu_pengurus', 'shu_dana_sosial', 'shu_pendidikan']
    .reduce((s, k) => s + (Number(settings.value[k]) || 0), 0)
)

async function load() {
  const { data } = await client.get('/settings')
  settings.value = { ...settings.value, ...data }
}

async function save() {
  try {
    await client.put('/settings', settings.value)
    ui.notify('Pengaturan disimpan')
  } catch (e) {
    ui.notify('Gagal menyimpan pengaturan', 'error')
  }
}

async function backup() {
  // unduh file koperasi.db (lewat axios agar token terkirim)
  try {
    const res = await client.get('/settings/backup', { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'koperasi-backup.db'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ui.notify('Gagal mengunduh backup', 'error')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h1>Pengaturan</h1>
    <p class="sub">Identitas koperasi, printer, dan backup data</p>

    <div class="card">
      <label>
        Nama Koperasi
        <input v-model="settings.coop_name" />
      </label>
      <label>
        Alamat
        <textarea v-model="settings.coop_address" rows="2" />
      </label>
      <div class="row">
        <label>
          Ukuran Printer Kwitansi
          <select v-model="settings.printer_size">
            <option value="58mm">Thermal 58mm</option>
            <option value="a4">A4</option>
          </select>
        </label>
        <label>
          Denda Keterlambatan / Hari (Rp)
          <CurrencyInput
            :model-value="Number(settings.late_fee_per_day) || 0"
            @update:model-value="settings.late_fee_per_day = String($event)"
          />
        </label>
      </div>
      <div class="row">
        <label>
          Batas Pinjaman Tanpa Jaminan (Rp)
          <CurrencyInput
            :model-value="Number(settings.max_loan_without_collateral) || 0"
            @update:model-value="settings.max_loan_without_collateral = String($event)"
          />
        </label>
      </div>

      <h3 class="section">Alokasi SHU (%)
        <span :class="['total', shuTotal === 100 ? 'ok' : 'warn']">Total: {{ shuTotal }}%</span>
      </h3>
      <div class="shu-grid">
        <label>Cadangan<input v-model="settings.shu_cadangan" type="number" /></label>
        <label>Jasa Modal<input v-model="settings.shu_jasa_modal" type="number" /></label>
        <label>Jasa Usaha<input v-model="settings.shu_jasa_usaha" type="number" /></label>
        <label>Pengurus<input v-model="settings.shu_pengurus" type="number" /></label>
        <label>Dana Sosial<input v-model="settings.shu_dana_sosial" type="number" /></label>
        <label>Pendidikan<input v-model="settings.shu_pendidikan" type="number" /></label>
      </div>

      <div class="actions">
        <button class="btn ghost" @click="backup">⬇ Backup Database</button>
        <button class="btn" @click="save">Simpan Pengaturan</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--primary-dark);
}
.sub {
  margin: 2px 0 20px;
  color: var(--muted);
  font-size: 0.85rem;
}
.card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.section {
  margin: 8px 0 0;
  font-size: 0.95rem;
  color: var(--primary-dark);
  border-top: 1px solid var(--border);
  padding-top: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.total {
  font-size: 0.78rem;
  padding: 2px 10px;
  border-radius: 999px;
}
.total.ok {
  background: #dcfce7;
  color: #166534;
}
.total.warn {
  background: #fee2e2;
  color: #991b1b;
}
.shu-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 560px) {
  .shu-grid {
    grid-template-columns: 1fr 1fr;
  }
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
