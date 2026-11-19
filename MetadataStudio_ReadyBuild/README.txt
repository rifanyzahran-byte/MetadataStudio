METADATA STUDIO - WINDOWS PORTABLE

Aplikasi mengubah metadata video langsung di file asli. Untuk pemrosesan lossless, FFmpeg membuat file sementara dalam folder yang sama, lalu mengganti file asli jika proses berhasil. Tidak ada salinan permanen. File yang telah berhasil diubah tidak bisa dikembalikan otomatis.

CARA MENDAPATKAN EXE:
1. Upload seluruh isi paket ini ke repository GitHub baru (termasuk folder .github/workflows).
2. Buka tab Actions > Build Metadata Studio Windows EXE > Run workflow.
3. Setelah selesai, unduh artifact MetadataStudio_Windows_Portable.
4. Ekstrak ZIP, buka MetadataStudio.exe. Tidak perlu instal Python atau FFmpeg.

FITUR:
- Scan satu folder atau subfolder
- Edit file asli (in-place), atau output terpisah
- Inspect metadata via ffprobe; export JSON/CSV
- Remux tanpa re-encode; ubah tanggal, title, artist, comment
- Progress, stop setelah file berjalan selesai, log kegagalan
- Opsi ExifTool membutuhkan exiftool.exe terpisah di folder aplikasi atau PATH

PERINGATAN:
- Uji pada file yang tidak penting dahulu. Simpan backup sendiri untuk video berharga.
- File sementara membutuhkan ruang disk sebesar video yang diproses.
- Remux tidak menghapus semua metadata tersembunyi dalam bitstream, watermark, fingerprint visual/audio, atau jejak sistem file.
- Mengubah metadata tidak menjamin peningkatan views atau perubahan pengenalan konten oleh YouTube.
- Build dilakukan di GitHub Windows runner; file EXE tidak termasuk dalam paket sumber ini.
