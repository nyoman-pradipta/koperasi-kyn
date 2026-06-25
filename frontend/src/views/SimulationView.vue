<script setup>
import CreditSimulation from '../components/CreditSimulation.vue'
</script>

<template>
  <div>
    <h1>Simulasi Kredit</h1>
    <p class="sub">Hitung angsuran, biaya, dan dana bersih sebelum pengajuan</p>
    <CreditSimulation />
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
</style>
