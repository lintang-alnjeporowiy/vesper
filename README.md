# TPT Planner

Pendekatan baru untuk tugas mata kuliah **Perencanaan Transportasi Laut (TPT, MS234501)** di Departemen Teknik Transportasi Laut, Fakultas Teknologi Kelautan (FTK), Institut Teknologi Sepuluh Nopember (ITS) Surabaya.

Tugas TPT meminta mahasiswa merencanakan angkutan laut untuk sebuah kawasan industri atau KEK. Pengerjaannya meliputi:

- analisis permintaan (proyeksi arus barang inbound/outbound);
- pemilihan kapal dan jumlah armada per rute (RTD, frekuensi, utilisasi);
- biaya angkutan (TCH, BBM, biaya pelabuhan);
- perencanaan terminal khusus (TERSUS): fasilitas perairan dan daratan, alat bongkar muat, BOR, investasi, dan tata letak.

Biasanya semua itu dikerjakan dalam satu workbook Excel besar dengan Solver. TPT Planner memindahkan model tersebut ke aplikasi yang terdiri dari tiga bagian:

- **engine Python** yang rumusnya terdokumentasi dan dites terhadap workbook asli. Kesalahan rumus yang ditemukan di Excel dicatat sebagai temuan audit A1–A15 dan dikoreksi di engine.
- **API** (FastAPI).
- **UI web** (React) yang mengikuti alur pengerjaan tugas. Setiap angka bisa ditelusuri ke rumus dan inputnya.

Dengan begitu skenario (kapal, alat, harga BBM, kurs, pertumbuhan muatan) bisa diubah dan hasilnya langsung terlihat, tanpa menyusun ulang rumus di spreadsheet.

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
