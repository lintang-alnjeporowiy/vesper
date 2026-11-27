<p align="center">
  <img src="logo/VESPER.png" alt="Vesper" width="360" />
</p>

<p align="center"><em>Akuntan yang duduk di samping perencana armada Anda: ia tidak ikut bertaruh, tapi tahu persis ke mana setiap rupiah pergi.</em></p>

---

Dalam *Casino Royale*, Vesper Lynd adalah akuntan Treasury yang dikirim untuk mengawasi dana taruhan James Bond. Ia tidak memegang kartu. Tugasnya memastikan setiap chip bisa dipertanggungjawabkan, dan ia tidak segan bertanya ketika ada angka yang tidak masuk akal.

**Vesper** mengambil peran yang sama untuk tugas mata kuliah **Perencanaan Transportasi Laut (TPT, MS234501)** di Departemen Teknik Transportasi Laut, Fakultas Teknologi Kelautan (FTK), Institut Teknologi Sepuluh Nopember (ITS) Surabaya. Anda yang memilih kapal, alat, dan tata letak terminal; Vesper yang mencatat biayanya, menelusuri asal setiap angka, dan menunjukkan rumus mana yang keliru.

## Meja permainannya

Tugas TPT meminta mahasiswa merencanakan angkutan laut untuk sebuah kawasan industri atau KEK:

- analisis permintaan (proyeksi arus barang inbound/outbound);
- pemilihan kapal dan jumlah armada per rute (RTD, frekuensi, utilisasi);
- biaya angkutan (TCH, BBM, biaya pelabuhan);
- perencanaan terminal khusus (TERSUS): fasilitas perairan dan daratan, alat bongkar muat, BOR, investasi, dan tata letak.

Biasanya semua itu dikerjakan dalam satu workbook Excel besar dengan Solver. Taruhannya besar, sedangkan rumusnya tersebar di puluhan sheet.

## Cara Vesper bekerja

- **Buku besar yang bisa diaudit.** Engine Python dengan rumus terdokumentasi, dites terhadap workbook asli. Setiap kekeliruan rumus di Excel dicatat sebagai temuan audit (A1–A30 sejauh ini) dan dikoreksi di engine, tidak disembunyikan.
- **Setiap angka punya kuitansi.** UI web (React) mengikuti alur pengerjaan tugas, dan setiap angka bisa diklik untuk melihat rumus, input, dan sel Excel asalnya.
- **Tidak ada angka karangan.** Hasil yang belum dihitung engine diberi label `placeholder` sampai benar-benar dihitung.
- **Ganti taruhan, lihat hasilnya.** Kapal, alat, harga BBM, kurs, pertumbuhan muatan, pola bangun, atau eskalasi harga bisa diubah dan hasilnya langsung terlihat lewat API (FastAPI), tanpa menyusun ulang rumus di spreadsheet.

Proyek ini sedang dikembangkan. Dokumentasi teknis, tahapan, dan cara menjalankan ada di [v2/README.md](v2/README.md), [v2/docs/01_SPEC.md](v2/docs/01_SPEC.md), dan [v2/docs/02_ROADMAP.md](v2/docs/02_ROADMAP.md).

## Referensi tugas

Pengembangan memakai hasil tugas TPT kelompok-kelompok berikut sebagai acuan domain dan data pembanding. Terima kasih kepada para penyusunnya.

| Kelompok | Studi kasus | Penyusun | Dosen pembimbing | Peran di proyek ini |
|---|---|---|---|---|
| K15 | Kawasan Industri Batam, Kepulauan Riau (2024) | Febiola Gloria Puspa, Yudho Dwi Wibowo | Dr.-Ing. Ir. Setyo Nugroho | kasus utama dan golden test engine |
| K21 | Kawasan Industri Gresik, Jawa Timur (2024) | Thoriq Akbar Maulana, Bonita Rizki Pramesti | Maulana Yafie Danendra, S.T., M.Log. | uji lanjutan |
| K24 | Kawasan Industri Palu (2024) | Primo Rajendra Prayoga | Siti Dwi Lazuardi, S.T., M.Sc. | uji lanjutan |
| K7 | Impor jagung, pola hub-spoke | Nathania Nityasa Palastri, Boyce Rajamin | Ir. Siti Dwi Lazuardi, S.T., M.Sc. | referensi varian (di luar cakupan saat ini) |

Bahan asli (laporan, presentasi, workbook) tidak disertakan di repositori ini.

<sub>Nama Vesper adalah penghormatan pada tokoh fiksi Vesper Lynd. Proyek ini tidak berafiliasi dengan pemegang hak waralaba James Bond.</sub>
