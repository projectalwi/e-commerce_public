# Proyek Analisis Data: E-Commerce Public Dataset

Analisis data e-commerce Brasil (September 2016 - Oktober 2018) beserta dashboard Streamlit.

## Pertanyaan Bisnis

1. Kategori produk apa yang punya rata-rata review score terendah dan persentase ulasan buruk (1-2 bintang) tertinggi, dan mana yang harus diprioritaskan untuk evaluasi kualitas?
2. Bagaimana perubahan pendapatan bulanan (harga + ongkir) per kategori selama Jan 2017 - Agu 2018, dan berapa perkiraan pendapatan dua kuartal berikutnya?
3. Kelompok pelanggan apa yang terbentuk berdasarkan Recency dan Monetary, berapa kontribusi pendapatannya, dan mana yang diprioritaskan untuk retensi/win-back?

## Struktur Folder

```text
.
├── E_Commerce_Public_Dataset.ipynb
├── dashboard/
│   ├── dashboard.py
│   └── main_data.csv
├── data/
├── requirements.txt
├── README.md
├── .gitignore
└── url.txt
```

## Menjalankan Notebook

Letakkan 9 file CSV dataset di folder yang sama dengan notebook (sel `read_csv` membaca nama file langsung), lalu jalankan semua sel.

Sel terakhir akan membuat ulang `dashboard/main_data.csv`.

## Menjalankan Dashboard (Lokal)

Disarankan menggunakan Python 3.10 atau lebih baru.

### 1. Clone Repository

```bash
git clone YOUR_REPOSITORY_URL
cd "E-Commerce Public Dataset"
```

### 2. Create Virtual Environment

Buat virtual environment menggunakan perintah:

```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

Untuk Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Untuk Windows Command Prompt (CMD):

```cmd
.venv\Scripts\activate.bat
```

### 4. Install Dependencies

Pastikan virtual environment sudah aktif, kemudian instal seluruh library yang dibutuhkan:

```bash
python -m pip install -r requirements.txt
```

### 5. Run the Dashboard

Jalankan aplikasi Streamlit:

```bash
streamlit run dashboard/dashboard.py
```

## Deploy ke Streamlit Community Cloud

Push folder project ini ke GitHub, buat app baru di [Streamlit Community Cloud](https://share.streamlit.io), pilih `dashboard/dashboard.py` sebagai main file, lalu salin URL aplikasi ke `url.txt`.

## Catatan Metode

- Pesanan `canceled` dan `unavailable` tidak dihitung di analisis kualitas, pendapatan, maupun RFM.
- Perkiraan pendapatan memakai rata-rata bergerak 3 bulan (error backtest 9-13%), tanpa efek musiman.
- RFM memakai skor kuartil untuk Recency dan Monetary; Frequency tidak dipakai karena sekitar 97% pelanggan hanya membeli sekali.

## Author

Alwi Nur Firdaus