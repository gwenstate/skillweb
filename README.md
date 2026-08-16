# SKILLWEB
Webcam project pake Python, OpenCV, sama MediaPipe. Ada 2 mode yang bisa di-switch langsung pake tangan, gak perlu keyboard atau mouse buat main-mainnya.

## SPIDER MODE
Bentuk tangan kayak web-shooter Spider-Man — jempol, telunjuk, kelingking lurus keluar, jari tengah sama manis dilipet ke dalem. Double tap (bentuk-lepas-bentuk cepet) buat trigger nembak.
Tiap tangan punya siklus 4 efek yang gantian tiap kali nembak:
1. Particle burst biasa
2. Particle yang "nembus" ke arah kamera (kalo tangan ngarah ke lensa)
3. Web pattern statis yang muncul terus fade
4. Web yang nempel permanen di frame

## GUN MODE
Pegang benda apa aja, terus sentak cepet ke arah kamera. Trigger-nya dari deteksi gerakan mendadak (motion detection), bukan gesture tangan kayak WEB mode. Jadi kalo gerakannya tiba-tiba jauh lebih cepet dari gerakan biasa, itu dianggap tembakan.
Ada target musuh yang muncul random di layar. Kena target, score naik dan combo nambah. Meleset, combo balik ke 0. Target-nya bisa di-toggle on/off pake tombol `E`, buat jaga-jaga kalo lagi gak mau ada game-nya.
Cara ganti mode tinggal nempelin ujung telunjuk ke tombol WEB atau GUN di pojok atas layar, tahan bentar sampe penuh.

## Menjalankan Proyek

Pake Python 3.11 ya, jangan yang lebih baru — MediaPipe belom compatible sama versi baru pas project ini dibikin (ini sempet bikin stuck lama banget ).

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Terus download model hand landmark-nya (gak ikut di-push ke repo soalnya ukurannya lumayan gede, sekitar 7MB):

```
curl -L -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

Jalanin:

```
python main.py
```

`q` buat keluar, `E` buat toggle target musuh (khusus mode gun).

## Isi foldernya

- `main.py` — loop utama, mode switching, gabungin semuanya
- `hand_tracker.py` — wrapper MediaPipe, deteksi gesture web-shooter
- `object_tracker.py` — motion detection buat trigger di gun mode
- `effects.py` — particle system, web pattern, semua efek visual
- `enemies.py` — target musuh, score, combo
- `sound.py` — sound effect-nya di-generate sendiri pake numpy (sine wave, noise), diputer pake winsound bawaan Windows, gak pake file audio dari luar sama sekali

## Cerita di baliknya dikit
yang bisa nyasar.
GUN mode awalnya gak kayak sekarang. Percobaan pertama pake object tracker (CSRT terus MIL) buat ngikutin benda yang dipegang, tapi gagal mulu — soalnya justru pas gerakan cepet (yang emang dibutuhin buat "sentakan"-nya), tracker malah paling gampang kehilangan objek gara-gara motion blur. Percobaan kedua coba color detection (kalibrasi warna dari bendanya), eh malah ke-detect nyasar ke background yang warnanya mirip.
Akhirnya pindah ke pendekatan paling simpel: frame differencing, bandingin frame sekarang sama sebelumnya, kalo ada area yang berubah gede dan cepet ya itu dianggap gerakan. Ternyata ini yang paling robust buat kasus sentakan cepat kayak gini — gak butuh kalibrasi apa-apa, dan gak ada state 
