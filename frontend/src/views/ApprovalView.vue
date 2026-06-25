<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../api/client'
import { useUiStore } from '../stores/ui'
import { useCurrency } from '../composables/useCurrency'

const router = useRouter()
const ui = useUiStore()
const { rp } = useCurrency()

const pending = ref([])

async function load() {
  const { data } = await client.get('/loans', { params: { status: 'pending', page_size: 100 } })
  pending.value = data.items
}

async function decide(loan, action) {
  const note =
    action === 'approve'
      ? prompt('Catatan persetujuan (opsional):') || ''
      : prompt('Alasan penolakan:') || ''
  try {
    await client.post(`/loans/${loan.id}/${action}`, { note })
    ui.notify(action === 'approve' ? 'Pinjaman disetujui' : 'Pinjaman ditolak')
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Aksi gagal', 'error')
  }
}

const DOC_STATUS = { sudah_diterima: 'Sudah Diterima', belum_diterima: 'Belum Diterima' }

onMounted(load)
</script>

<template>
  <div>
    <h1>Persetujuan Kredit</h1>
    <p class="sub">{{ pending.length }} pengajuan menunggu keputusan</p>

    <div v-if="pending.length === 0" class="empty card">
      Tidak ada pengajuan yang menunggu persetujuan. 🎉
    </div>

    <table v-else class="tbl">
      <thead>
        <tr>
          <th>No Pengajuan</th>
          <th>Anggota</th>
          <th class="num">Nominal</th>
          <th>Jaminan</th>
          <th>Dokumen Asli</th>
          <th>Aksi</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in pending" :key="l.id">
          <td><strong>{{ l.loan_number }}</strong></td>
          <td>{{ l.member_name }}</td>
          <td class="num">{{ rp(l.principal_amount) }}</td>
          <td>
            <span v-if="l.collateral" class="col-type">{{ l.collateral.type }}</span>
            <span v-else class="muted">—</span>
          </td>
          <td>
            <span v-if="l.collateral"
              :class="['doc-badge', l.collateral.doc_status === 'sudah_diterima' ? 'ok' : 'warn']">
              {{ DOC_STATUS[l.collateral.doc_status] || l.collateral.doc_status }}
            </span>
            <span v-else class="muted">—</span>
          </td>
          <td>
            <div class="acts">
              <button class="link" @click="router.push(`/pinjaman/${l.id}`)">Detail</button>
              <button class="btn danger" @click="decide(l, 'reject')">Tolak</button>
              <button class="btn" @click="decide(l, 'approve')">Setujui</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 20px; color: var(--muted); font-size: 0.85rem; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
.empty { text-align: center; color: var(--muted); padding: 40px; }
.tbl { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; font-size: 0.88rem; }
.tbl th { background: #f1f5f9; padding: 10px 14px; text-align: left; font-weight: 600; border-bottom: 1px solid var(--border); }
.tbl td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.tbl tr:last-child td { border-bottom: none; }
.num { text-align: right; }
.col-type { font-size: 0.82rem; font-weight: 600; color: var(--primary-dark); }
.doc-badge { font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; }
.doc-badge.ok { background: #dcfce7; color: #166534; }
.doc-badge.warn { background: #fef3c7; color: #92400e; }
.muted { color: var(--muted); font-size: 0.82rem; }
.acts { display: flex; gap: 6px; align-items: center; }
.btn { padding: 7px 13px; background: var(--primary); color: #fff; border: none; border-radius: 7px; font-weight: 600; cursor: pointer; font-size: 0.82rem; }
.btn:hover { background: var(--primary-dark); }
.btn.danger { background: #b91c1c; }
.link { border: none; background: none; cursor: pointer; color: var(--primary); font-size: 0.82rem; }
</style>
