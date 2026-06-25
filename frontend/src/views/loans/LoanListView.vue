<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'
import { useCurrency } from '../../composables/useCurrency'

const router = useRouter()
const { rp } = useCurrency()

const loans = ref([])
const total = ref(0)
const statusFilter = ref('')
const search = ref('')

const STATUS = ['', 'draft', 'pending', 'approved', 'active', 'rejected', 'paid_off']
const COL_LABEL = {
  available: 'Tersedia',
  in_use: 'Sedang Digunakan',
  returned: 'Dikembalikan',
  archived: 'Diarsipkan',
}

async function load() {
  const { data } = await client.get('/loans', {
    params: {
      status: statusFilter.value || undefined,
      search: search.value || undefined,
      page_size: 100,
    },
  })
  loans.value = data.items
  total.value = data.total
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Data Pinjaman</h1>
        <p class="sub">{{ total }} pinjaman</p>
      </div>
      <button class="btn" @click="router.push('/pengajuan')">+ Pengajuan Baru</button>
    </div>

    <div class="toolbar">
      <input v-model="search" class="search" placeholder="Cari no pinjaman / nama…" @keyup.enter="load" />
      <select v-model="statusFilter" @change="load">
        <option v-for="s in STATUS" :key="s" :value="s">{{ s || 'Semua status' }}</option>
      </select>
      <button class="btn ghost" @click="load">Cari</button>
    </div>

    <div class="card">
      <table class="tbl">
        <thead>
          <tr>
            <th>No. Pinjaman</th>
            <th>Nama</th>
            <th class="num">Pokok</th>
            <th class="num">Total Bayar</th>
            <th>Bunga</th>
            <th>Status</th>
            <th>Jaminan</th>
            <th class="num">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loans.length === 0"><td colspan="8" class="empty">Belum ada pinjaman.</td></tr>
          <tr v-for="l in loans" :key="l.id">
            <td>{{ l.loan_number }}</td>
            <td>{{ l.member_name }}</td>
            <td class="num">{{ rp(l.principal_amount) }}</td>
            <td class="num">{{ rp(l.total_payable) }}</td>
            <td>{{ l.interest_type }} {{ l.interest_rate }}%</td>
            <td><span class="badge" :class="l.status">{{ l.status }}</span></td>
            <td>
              <template v-if="l.collateral">
                <div class="col-cell">
                  <span class="col-type">{{ l.collateral.type }}</span>
                  <span class="col-badge" :class="'col-' + l.collateral.collateral_status">{{ COL_LABEL[l.collateral.collateral_status] || l.collateral.collateral_status }}</span>
                </div>
              </template>
              <span v-else-if="!l.requires_collateral" class="col-badge col-available">Tanpa Jaminan</span>
              <span v-else class="no-col">—</span>
            </td>
            <td class="num">
              <button class="link" @click="router.push(`/pinjaman/${l.id}`)">Detail</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.85rem; }
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.search { flex: 1; max-width: 320px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; }
select { padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.tbl th, .tbl td { padding: 11px 14px; text-align: left; border-bottom: 1px solid var(--border); }
.tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.num { text-align: right; }
.empty { text-align: center; color: var(--muted); padding: 26px; }
.badge { padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; text-transform: capitalize; }
.badge.draft { background: #f1f5f9; color: #475569; }
.badge.pending { background: #fef3c7; color: #92400e; }
.badge.approved { background: #dbeafe; color: #1e40af; }
.badge.active { background: #dcfce7; color: #166534; }
.badge.rejected { background: #fee2e2; color: #991b1b; }
.badge.paid_off { background: #e0e7ff; color: #3730a3; }
.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.link { border: none; background: none; cursor: pointer; color: var(--primary); font-size: 0.85rem; }
.col-cell { display: flex; flex-direction: column; gap: 3px; }
.col-type { font-size: 0.8rem; color: var(--text); }
.col-badge { font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; width: fit-content; }
.col-available  { background: #dcfce7; color: #166534; }
.col-in_use     { background: #fef3c7; color: #92400e; }
.col-returned   { background: #dbeafe; color: #1e40af; }
.col-archived   { background: #f1f5f9; color: #475569; }
.no-col { color: var(--muted); font-size: 0.85rem; }
</style>
