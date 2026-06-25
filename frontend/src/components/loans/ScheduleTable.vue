<script setup>
import { useCurrency } from '../../composables/useCurrency'

// rows: [{ no, due_date?, principal, interest, total, status? }]
defineProps({
  rows: { type: Array, default: () => [] },
  showDue: { type: Boolean, default: false },
  showStatus: { type: Boolean, default: false },
})
const { rp } = useCurrency()
</script>

<template>
  <table class="tbl striped">
    <thead>
      <tr>
        <th>Bln</th>
        <th v-if="showDue">Jatuh Tempo</th>
        <th class="num">Pokok</th>
        <th class="num">Bunga</th>
        <th class="num">Total Angsuran</th>
        <th v-if="showStatus">Status</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="r in rows" :key="r.no">
        <td>{{ r.no }}</td>
        <td v-if="showDue">{{ r.due_date }}</td>
        <td class="num">{{ rp(r.principal) }}</td>
        <td class="num">{{ rp(r.interest) }}</td>
        <td class="num strong">{{ rp(r.total) }}</td>
        <td v-if="showStatus">
          <span class="badge" :class="r.status">{{ r.status }}</span>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.tbl th,
.tbl td {
  padding: 8px 12px;
  border: 1px solid var(--border);
  text-align: left;
}
.tbl th {
  background: #f1f5f9;
  font-weight: 600;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.strong {
  font-weight: 700;
}
.striped tbody tr:nth-child(even) {
  background: #fafafa;
}
.badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}
.badge.paid {
  background: #dcfce7;
  color: #166534;
}
.badge.unpaid {
  background: #fef3c7;
  color: #92400e;
}
.badge.partial {
  background: #dbeafe;
  color: #1e40af;
}
</style>
