# User Guide: WireGuard VPN Portal

## Overview

Sebagai user, Anda bisa:
- Add multiple devices (max sesuai limit yang ditentukan admin)
- Download VPN configuration
- View QR code untuk mobile setup
- Monitor connection status
- View network usage
- Revoke devices sendiri

## Getting Started

### 1. Login

1. Buka portal web
2. Masukkan username dan password LDAP Anda
3. Klik **Login**

### 2. Check VPN Access Status

Setelah login, Anda akan melihat:
- VPN access status (enabled/disabled)
- Maximum devices allowed
- Current device count

Jika VPN access disabled, hubungi administrator.

## Device Management

### Add New Device

1. Navigate ke **My Devices**
2. Klik **Add Device**
3. Masukkan device name (contoh: "My Laptop", "iPhone")
4. Klik **Create**
5. **IMPORTANT:** Simpan private key dan config dengan aman!
   - Private key hanya ditampilkan sekali
   - QR code akan expire dalam 30 menit

### View My Devices

1. Navigate ke **My Devices**
2. View list semua devices Anda:
   - Device name
   - VPN IP address
   - Status (active/revoked)
   - Connection status
   - Network usage
   - Last seen

### Download Configuration

1. Navigate ke **My Devices**
2. Pilih device
3. Klik **Download Config**
4. File `.conf` akan di-download
5. Import ke WireGuard client

### View QR Code

1. Navigate ke **My Devices**
2. Pilih device
3. Klik **View QR Code**
4. Scan dengan WireGuard mobile app

**Note:** QR code expire dalam 30 menit. Jika expired, regenerate QR code.

### Regenerate QR Code

1. Navigate ke **My Devices**
2. Pilih device
3. Klik **Regenerate QR Code**
4. QR code baru akan di-generate (expire dalam 30 menit)

### Revoke Device

1. Navigate ke **My Devices**
2. Pilih device yang ingin di-revoke
3. Klik **Revoke**
4. Confirm revocation
5. Device akan dihapus dari WireGuard dan tidak bisa digunakan lagi

## Connection Setup

### Desktop (Windows/Mac/Linux)

1. Download WireGuard client dari https://www.wireguard.com/install/
2. Install WireGuard
3. Download config file dari portal
4. Import config ke WireGuard
5. Activate connection

### Mobile (iOS/Android)

1. Install WireGuard app dari App Store/Play Store
2. Login ke portal
3. View QR code untuk device
4. Scan QR code dengan WireGuard app
5. Activate connection

## Monitoring

### Connection Status

- **Active:** Device terhubung ke VPN
- **Inactive:** Device tidak terhubung (tapi masih active)
- **Revoked:** Device sudah di-revoke

### Network Usage

View network usage untuk setiap device:
- Download (RX)
- Upload (TX)
- Total usage
- Bandwidth limit (jika ada)

### Last Seen

Last seen menunjukkan kapan terakhir kali device terhubung ke VPN.

## Troubleshooting

### Tidak bisa add device
- Check VPN access status (harus enabled)
- Check device limit (mungkin sudah mencapai max)
- Hubungi administrator jika masalah berlanjut

### QR code expired
- Regenerate QR code dari portal
- Atau download config file dan import manual

### Device tidak bisa connect
- Check device status (harus active)
- Verify WireGuard configuration
- Check internet connection
- Restart WireGuard client
- Hubungi administrator jika masalah berlanjut

### Lupa private key
- Private key tidak bisa di-retrieve
- Revoke device lama dan buat device baru
- Simpan private key dengan aman di device baru

### Device limit reached
- Revoke device yang tidak digunakan
- Atau hubungi administrator untuk increase limit

## Security Tips

1. **Simpan Private Key dengan Aman**
   - Private key hanya ditampilkan sekali
   - Simpan di password manager atau secure location
   - Jangan share private key dengan siapapun

2. **Revoke Unused Devices**
   - Revoke devices yang tidak digunakan lagi
   - Revoke jika device hilang atau dicuri

3. **Monitor Your Devices**
   - Check connection status regularly
   - Review network usage untuk detect suspicious activity
   - Report suspicious activity ke administrator

4. **Keep Devices Updated**
   - Update WireGuard client regularly
   - Update device OS dan security patches

## Support

Jika Anda mengalami masalah:
1. Check troubleshooting section di atas
2. Review device status dan logs
3. Hubungi administrator dengan informasi:
   - Username
   - Device name
   - Error message
   - Screenshot (jika ada)
