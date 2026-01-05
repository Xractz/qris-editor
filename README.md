# QRIS Editor

Tools CLI Python untuk membaca (decode), memvalidasi, dan mengedit kode QRIS (Quick Response Code Indonesian Standard).

## Fitur

- Decode QRIS dari gambar
- Validasi struktur dan checksum QRIS
- Edit nama merchant, kota, dan kode pos
- Generate QR code dengan template resmi QRIS
- Tanda "EDITED" pada output untuk identifikasi jika QRIS telah diubah

## Tentang QRIS

QRIS adalah standar kode QR untuk pembayaran yang ditetapkan oleh Bank Indonesia, mengadopsi spesifikasi **EMV QR Code Specification for Payment Systems** dari **EMVCo**.

### Format TLV (Tag-Length-Value)

```
5906Xractz
││└──────── Value (6 karakter)
│└───────── Length = 06
└────────── Tag = 59 (Merchant Name)
```

### Contoh Breakdown QRIS

Raw QRIS:

```
00020101021126570011ID.DANA.WWW011893600915331522899202093152289920303UMI51440014ID.CO.QRIS.WWW0215ID10222053846400303UMI5204481453033605802ID5906Xractz6009Indonesia61051011063048FDF
```

| Tag | Length | Value                                    | Keterangan                   |
| --- | ------ | ---------------------------------------- | ---------------------------- |
| 00  | 02     | 01                                       | Payload Format Indicator     |
| 01  | 02     | 11                                       | Point of Initiation (Static) |
| 26  | 57     | 0011ID.DANA.WWW0118936009153315228992... | Merchant Account Info        |
| 51  | 44     | 0014ID.CO.QRIS.WWW0215ID1022205384640... | QRIS Merchant Info           |
| 52  | 04     | 4814                                     | Merchant Category Code       |
| 53  | 03     | 360                                      | Currency (IDR)               |
| 58  | 02     | ID                                       | Country Code                 |
| 59  | 06     | Xractz                                   | Merchant Name                |
| 60  | 09     | Indonesia                                | Merchant City                |
| 61  | 05     | 10110                                    | Postal Code                  |
| 63  | 04     | 8FDF                                     | Checksum (CRC-16)            |

### Struktur Tag QRIS

| Tag  | Nama                                | Keterangan                                          |
| ---- | ----------------------------------- | --------------------------------------------------- |
| 00   | Payload Format Indicator            | Indikator untuk EMVCo                               |
| 01   | Point of Initiation Method          | Jenis metode inisiasi (11=Statis, 12=Dinamis)       |
| 26   | Merchant Account Information        | Custom field untuk acquirer                         |
| ↳ 00 | Acquirer ID                         | Situs acquirer (ID.DANA.WWW, ID.CO.SHOPEE.WWW, dll) |
| ↳ 01 | MPAN                                | Merchant Primary Account Number                     |
| ↳ 02 | Terminal Identifier                 | Terminal identifier                                 |
| ↳ 03 | Kategori Usaha                      | UMI/UME/UBE                                         |
| 51   | Merchant Account Information (QRIS) | Custom field untuk switching                        |
| ↳ 00 | Switching ID                        | Situs switching (ID.CO.QRIS.WWW)                    |
| ↳ 02 | NMID                                | National Merchant ID                                |
| ↳ 03 | Kategori Usaha                      | UMI/UME/UBE                                         |
| 52   | Merchant Category Code              | Kode kategori merchant sesuai ISO 18245             |
| 53   | Transaction Currency                | Kode mata uang sesuai ISO 4217 (360=IDR)            |
| 58   | Country Code                        | Kode negara sesuai ISO 3166-1 alpha 2               |
| 59   | Merchant Name                       | Nama merchant                                       |
| 60   | Merchant City                       | Kota merchant                                       |
| 61   | Postal Code                         | Kode pos                                            |
| 62   | Additional Data Field               | Field tambahan (opsional)                           |
| ↳ 07 | Terminal Label                      | Label terminal (A01, B01, dll)                      |
| 63   | CRC                                 | Cyclic Redundancy Check (CRC-16/IBM_3740)           |

### Checksum

Checksum QRIS menggunakan algoritma **CRC-16/IBM_3740**. Format: `6304XXXX` dimana `XXXX` adalah 4 digit hex.

**Cara menentukan tipe CRC:**

Untuk memverifikasi tipe checksum yang digunakan QRIS, bisa menggunakan [CRC Calculator](https://crccalc.com/). Contoh:

```
Data: 00020101021126570011ID.DANA.WWW...6009Indonesia6105101106304
CRC:  8FDF
```

[Verify CRC](https://crccalc.com/?crc=00020101021126570011ID.DANA.WWW011893600915331522899202093152289920303UMI51440014ID.CO.QRIS.WWW0215ID10222053846400303UMI5204481453033605802ID5906Xractz6009Indonesia6105101106304&method=&datatype=ascii&outtype=hex) → hasil CRC-16/IBM-3740 = **8FDF** ✓

## Instalasi

```bash
pip install -r requirements.txt
```

## Penggunaan

```bash
python qris_editor.py
```

**Alur:**

1. Masukkan path gambar QRIS
2. Tools akan memvalidasi dan menampilkan informasi merchant
3. Edit nama merchant, kota, atau kode pos (Enter untuk skip)
4. QR code baru tersimpan dengan template resmi

## Validasi QRIS

Tools melakukan validasi otomatis:

- Panjang minimum (>50 karakter)
- Format header (dimulai dengan `000201`)
- Keberadaan checksum (Tag 63)
- Verifikasi checksum CRC-16/IBM_3740
- Tag wajib (Merchant Name)
- Limit panjang: Nama (25), Kota (15), Kode Pos (5)

## Catatan Penting

> [!WARNING]
> QRIS yang telah diedit **tidak dapat digunakan untuk pembayaran** pada sebagian besar aplikasi.
>
> Server QRIS nasional melakukan validasi **NMID + Nama Merchant** terhadap database pusat.
> Jika nama merchant tidak cocok dengan NMID yang terdaftar, transaksi akan ditolak.

### Hasil Testing Pembayaran

| Aplikasi         | Status      | Keterangan                      |
| ---------------- | ----------- | ------------------------------- |
| mBanking BCA     | ❌ Gagal    | "Merchant tidak ditemukan"      |
| ShopeePay        | ❌ Gagal    | Transaksi ditolak               |
| GoPay            | ❌ Gagal    | "03 - Merchant tidak ditemukan" |
| **Wondr by BNI** | ✅ Berhasil | Transaksi berhasil diproses     |

## Dependensi

| Library                | Fungsi                      |
| ---------------------- | --------------------------- |
| pyzbar                 | Decode QR code              |
| Pillow                 | Image processing & template |
| opencv-python-headless | Preprocessing gambar        |
| qrcode                 | Generate QR code            |
| crc                    | Kalkulasi checksum          |

## Referensi

- [EMVCo - QR Codes](https://www.emvco.com/emv-technologies/qr-codes/)
- [Bank Indonesia - Sosialisasi QRIS (PDF)](https://www.bi.go.id/id/edukasi/Documents/Bahan-Sosialisasi-QRIS.pdf)
- [Mencoba Memahami QRIS](https://blog.isan.eu.org/post/mencoba-memahami-qris)
- [EMVCo QR Specification (W3C)](https://www.w3.org/2020/Talks/emvco-qr-20201021.pdf)

## Disclaimer

**For educational purposes only.**

Tools ini dibuat untuk mempelajari struktur data QRIS dan spesifikasi EMVCo. Developer tidak bertanggung jawab atas penyalahgunaan tools ini.

## Lisensi

MIT License
