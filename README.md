# Proyek Analisis Data: E-Commerce Public Dataset

Analisis data e-commerce Brasil (September 2016 - Oktober 2018) beserta dashboard Streamlit.

## Pertanyaan bisnis
1. Kategori produk apa yang punya rata-rata review score terendah dan persentase ulasan buruk (1-2 bintang) tertinggi, dan mana yang harus diprioritaskan untuk evaluasi kualitas?
2. Bagaimana perubahan pendapatan bulanan (harga + ongkir) per kategori selama Jan 2017 - Agu 2018, dan berapa perkiraan pendapatan dua kuartal berikutnya?
3. Kelompok pelanggan apa yang terbentuk berdasarkan Recency dan Monetary, berapa kontribusi pendapatannya, dan mana yang diprioritaskan untuk retensi/win-back?

## Struktur folder
```
.
├── E_Commerce_Public_Dataset.ipynb   # wrangling, EDA, visualisasi, kesimpulan
├── dashboard/
│   ├── dashboard.py                  # aplikasi Streamlit
│   └── main_data.csv                 # data bersih hasil notebook (satu baris per item pesanan)
├── data/                             # 9 file CSV dataset asli (taruh di sini, atau di folder yang sama dengan notebook)
├── requirements.txt
├── README.md
└── url.txt                           # isi dengan link dashboard Streamlit Cloud
```

## Menjalankan notebook
Letakkan 9 file CSV dataset di folder yang sama dengan notebook (sel `read_csv` membaca nama file langsung), lalu jalankan semua sel.
Sel terakhir akan membuat ulang `dashboard/main_data.csv`.

## Menjalankan dashboard (lokal)
Disarankan Python 3.10 atau lebih baru.
```
pip install -r requirements.txt
streamlit run dashboard/dashboard.py
```

## Deploy ke Streamlit Community Cloud
Push folder ini ke GitHub, buat app baru di https://share.streamlit.io, pilih `dashboard/dashboard.py` sebagai main file, lalu salin URL aplikasi ke `url.txt`.

## Catatan metode
- Pesanan `canceled` dan `unavailable` tidak dihitung di analisis kualitas, pendapatan, maupun RFM.
- Perkiraan pendapatan memakai rata-rata bergerak 3 bulan (error backtest 9-13%), tanpa efek musiman.
- RFM memakai skor kuartil untuk Recency dan Monetary; Frequency tidak dipakai karena sekitar 97% pelanggan hanya membeli sekali.
