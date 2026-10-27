# 🏥 Health Content Multi-Agent Studio

Aplikasi Web & Pipeline Multi-Agent AI untuk memproduksi konten edukasi kesehatan media sosial dengan riset aktual, verifikasi medis ketat, dan pencegahan hoaks. Didukung oleh **Google Gemini 2.5 API** dan **Google Search Grounding**.

---

## 5 Agen Kolaboratif

1. **💡 Dr. Idea (Ideator)**: Merumuskan topik, target audiens, dan sudut pandang segar yang membongkar mitos.
2. **🌐 Nexus (Trend & Context Researcher)**: Menghubungkan ide dengan data aktual **Kemenkes RI**, **BPOM**, dan data surveilans **WHO** via Google Search Grounding.
3. **🎨 Canvas (Visual & Copy Creator)**: Merancang hook 3 detik, slide carousel, naskah caption, dan prompt generator gambar AI (Midjourney/Flux).
4. **🩺 Dr. Verif (Medical Fact-Checker)**: Mengaudit naskah dengan pedoman kedokteran ilmiah, menghapus klaim spekulatif tanpa bukti.
5. **🏛️ Rapat Pleno Editorial (Council)**: Sesi konsensus untuk mengevaluasi skor medis vs virality, merevisi catatan dokter, dan mengesahkan draf final.

---

## 🌐 Menjalankan Tampilan Web Browser (Direkomendasikan)

### 1. Masuk ke direktori proyek & aktifkan virtual environment
```bash
cd /Users/aquilando/.gemini/antigravity/scratch/health_agent_pipeline
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Atur Gemini API Key di file `.env`
```bash
echo "GEMINI_API_KEY=KUNCI_API_ANDA_DISINI" > .env
```

### 3. Jalankan Web Server
```bash
python3 server.py
```

### 4. Buka di Browser
Buka browser favorit Anda (Chrome/Safari) dan akses:
👉 **`http://localhost:8000`**

Di sana Anda akan menemukan:
* Kolom input teks bebas untuk memasukkan ide konten kesehatan.
* Animasi 5 agen yang bergerak dan berdenyut secara *real-time* saat AI Gemini bekerja.
* Transkrip rapat live antar-agen.
* Naskah final carousel, prompt visual AI, sitasi resmi Kemenkes/WHO, dan tombol salin 1-klik.

---

## 💻 Alternatif: Menjalankan via Terminal (CLI)
Jika ingin menjalankan tanpa browser:
```bash
python3 main.py
```
