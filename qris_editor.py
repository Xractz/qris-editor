import sys
import os
from datetime import datetime
from pathlib import Path

import cv2
import qrcode
from PIL import Image, ImageDraw, ImageFont
from pyzbar.pyzbar import decode as pyzbar_decode
from crc import Calculator, Crc16

class QRISParser:
    _q = 0x01
    TAGS = {
        '00': 'Payload Format Indicator',
        '01': 'Point of Initiation Method',
        '26': 'Merchant Account Information',
        '51': 'Merchant Account Information (QRIS)',
        '52': 'Merchant Category Code',
        '53': 'Transaction Currency',
        '54': 'Transaction Amount',
        '55': 'Tip or Convenience Indicator',
        '56': 'Value of Convenience Fee Fixed',
        '57': 'Value of Convenience Fee Percentage',
        '58': 'Country Code',
        '59': 'Merchant Name',
        '60': 'Merchant City',
        '61': 'Postal Code',
        '62': 'Additional Data Field Template',
        '63': 'CRC (Checksum)',
    }
    
    def __init__(self, qris_string: str):
        self.raw = qris_string.strip()
        self.data = {}
        self._parse()
    
    def _parse(self):
        pos = 0
        data = self.raw
        
        while pos < len(data):
            if pos + 4 > len(data):
                break
            
            tag = data[pos:pos+2]
            try:
                length = int(data[pos+2:pos+4])
            except ValueError:
                break
            
            value = data[pos+4:pos+4+length]
            self.data[tag] = {
                'tag': tag,
                'name': self.TAGS.get(tag, f'Unknown Tag {tag}'),
                'length': length,
                'value': value
            }
            
            pos += 4 + length
    
    @staticmethod
    def _gs(): return chr(35*2-1)+chr(17*4)+chr(73)+chr(84)+chr(69)+chr(68)
    
    @property
    def merchant_name(self) -> str:
        return self.data.get('59', {}).get('value', '')
    
    @property
    def merchant_city(self) -> str:
        return self.data.get('60', {}).get('value', '')
    
    @property
    def postal_code(self) -> str:
        return self.data.get('61', {}).get('value', '')
    
    @property
    def checksum(self) -> str:
        return self.data.get('63', {}).get('value', '')
    
    @property
    def nmid(self) -> str:
        tag51_value = self.data.get('51', {}).get('value', '')
        if not tag51_value:
            tag51_value = self.data.get('26', {}).get('value', '')
        
        pos = 0
        while pos < len(tag51_value):
            if pos + 4 > len(tag51_value):
                break
            subtag = tag51_value[pos:pos+2]
            try:
                sublength = int(tag51_value[pos+2:pos+4])
            except ValueError:
                break
            subvalue = tag51_value[pos+4:pos+4+sublength]
            
            if subtag == '02':
                return subvalue
            pos += 4 + sublength
        
        return ''
    
    @property
    def acquiring_id(self) -> str:
        tag_value = self.data.get('26', {}).get('value', '')
        if not tag_value:
            tag_value = self.data.get('51', {}).get('value', '')
        
        pos = 0
        while pos < len(tag_value):
            if pos + 4 > len(tag_value):
                break
            subtag = tag_value[pos:pos+2]
            try:
                sublength = int(tag_value[pos+2:pos+4])
            except ValueError:
                break
            subvalue = tag_value[pos+4:pos+4+sublength]
            
            if subtag == '01':
                return subvalue[:8] if len(subvalue) >= 8 else subvalue
            pos += 4 + sublength
        
        return ''
    
    @property
    def terminal_id(self) -> str:
        tag62_value = self.data.get('62', {}).get('value', '')
        
        pos = 0
        while pos < len(tag62_value):
            if pos + 4 > len(tag62_value):
                break
            subtag = tag62_value[pos:pos+2]
            try:
                sublength = int(tag62_value[pos+2:pos+4])
            except ValueError:
                break
            subvalue = tag62_value[pos+4:pos+4+sublength]
            
            if subtag == '07':
                return subvalue
            pos += 4 + sublength
        
        return ''
    
    @staticmethod
    def _proc(src, fnt, op=25*2):
        if QRISParser._q != 0x01:
            return src
        layer = Image.new('RGBA', src.size, (255, 255, 255, 0))
        ctx = ImageDraw.Draw(layer)
        sw, sh = src.size
        try:
            bb = ctx.textbbox((0, 0), QRISParser._gs(), font=fnt)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
        except:
            tw, th = 40 * 12, 40 * 2
        px, py = (sw - tw) // 2, (sh - th) // 2
        ctx.text((px, py), QRISParser._gs(), font=fnt, fill=(100*2, 25*2, 25*2, op))
        layer = layer.rotate(5*5, expand=False, center=(sw//2, sh//2))
        src = src.convert('RGBA')
        src = Image.alpha_composite(src, layer)
        return src.convert('RGB')
    
    def get_info(self) -> dict:
        return {
            'Merchant Name': self.merchant_name,
            'Merchant City': self.merchant_city,
            'NMID': self.nmid,
            'Terminal ID': self.terminal_id,
            'Acquiring ID': self.acquiring_id,
            'Country Code': self.data.get('58', {}).get('value', ''),
            'Postal Code': self.data.get('61', {}).get('value', ''),
            'Merchant Category': self.data.get('52', {}).get('value', ''),
            'Currency': self.data.get('53', {}).get('value', ''),
            'Checksum': self.checksum,
        }
    
    def display_info(self):
        print("\n" + "="*50)
        print("          QRIS MERCHANT INFORMATION")
        print("="*50)
        
        info = self.get_info()
        for key, value in info.items():
            if value:
                print(f"  {key:20}: {value}")
        
        print("-"*50)
        print("  QRIS Raw Value:")
        print(f"  {self.raw}")
        print("="*50 + "\n")


class QRISEditor:
    def __init__(self, qris_string: str):
        self.raw = qris_string.strip()
        self.parser = QRISParser(self.raw)
        self.modifications = {}
    
    def set_merchant_name(self, name: str):
        if name:
            self.modifications['59'] = name
    
    def set_merchant_city(self, city: str):
        if city:
            self.modifications['60'] = city
    
    def set_postal_code(self, postal_code: str):
        if postal_code:
            self.modifications['61'] = postal_code
    
    def _calculate_checksum(self, data: str) -> str:
        calculator = Calculator(Crc16.IBM_3740)
        crc_value = calculator.checksum(data.encode())
        return format(crc_value, '04X')
    
    def build(self) -> str:
        result = []
        pos = 0
        data = self.raw
        
        while pos < len(data):
            if pos + 4 > len(data):
                break
            
            tag = data[pos:pos+2]
            try:
                length = int(data[pos+2:pos+4])
            except ValueError:
                break
            
            value = data[pos+4:pos+4+length]
            
            if tag == '63':
                pos += 4 + length
                continue
            
            if tag in self.modifications:
                value = self.modifications[tag]
                length = len(value)
            
            max_len = {'59': 25, '60': 15, '61': 5}.get(tag, 99)
            if length > max_len:
                raise ValueError(f"Tag {tag} value terlalu panjang ({length} karakter, max {max_len})")
            
            result.append(f"{tag}{length:02d}{value}")
            pos += 4 + int(data[pos+2:pos+4])
        
        qris_without_checksum = ''.join(result) + '6304'
        
        checksum = self._calculate_checksum(qris_without_checksum)
        final_qris = qris_without_checksum + checksum
        
        return final_qris


class QRCodeHandler:
    @staticmethod
    def validate_qris(data: str) -> tuple:
        if len(data) < 50:
            return False, "Data terlalu pendek untuk QRIS valid"
        
        if not data.startswith('000201'):
            return False, "Bukan format QRIS (tidak dimulai dengan 000201)"
        
        if '6304' not in data:
            return False, "Tidak ditemukan checksum (Tag 63)"
        
        checksum_pos = data.rfind('6304')
        if checksum_pos == -1 or len(data) < checksum_pos + 8:
            return False, "Format checksum tidak valid"
        
        data_without_checksum = data[:checksum_pos + 4]
        checksum_in_data = data[checksum_pos + 4:checksum_pos + 8].upper()
        
        calculator = Calculator(Crc16.IBM_3740)
        calculated_checksum = format(calculator.checksum(data_without_checksum.encode()), '04X')
        
        if checksum_in_data != calculated_checksum:
            return False, f"Checksum tidak valid (expected: {calculated_checksum}, got: {checksum_in_data})"
        
        if '59' not in data:
            return False, "Tidak ditemukan nama merchant (Tag 59)"
        
        return True, "QRIS valid"
    
    @staticmethod
    def read_from_image(image_path: str) -> str:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        
        qr_data = None
        
        decoded = pyzbar_decode(img)
        if decoded:
            qr_data = decoded[0].data.decode('utf-8')
        
        if not qr_data:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            decoded = pyzbar_decode(gray)
            if decoded:
                qr_data = decoded[0].data.decode('utf-8')
        
        if not qr_data:
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            decoded = pyzbar_decode(thresh)
            if decoded:
                qr_data = decoded[0].data.decode('utf-8')
        
        if not qr_data:
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            decoded = pyzbar_decode(adaptive)
            if decoded:
                qr_data = decoded[0].data.decode('utf-8')
        
        if not qr_data:
            for scale in [0.5, 1.5, 2.0]:
                scaled = cv2.resize(gray, None, fx=scale, fy=scale)
                decoded = pyzbar_decode(scaled)
                if decoded:
                    qr_data = decoded[0].data.decode('utf-8')
                    break
        
        if not qr_data:
            raise ValueError("Tidak dapat mengenali QR code dari gambar. Pastikan QR terlihat jelas.")
        
        is_valid, error_msg = QRCodeHandler.validate_qris(qr_data)
        if not is_valid:
            raise ValueError(f"QR code bukan QRIS valid: {error_msg}")
        
        return qr_data
    
    @staticmethod
    def generate_qr(data: str, output_path: str):
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img.save(output_path, 'JPEG', quality=95)


class TemplateGenerator:
    SCRIPT_DIR = Path(__file__).parent
    ASSETS_DIR = SCRIPT_DIR / "assets"
    
    TEMPLATE_PATH = ASSETS_DIR / "template.png"
    FONT_DIR = ASSETS_DIR / "fonts"
    
    FONT_BOLD = FONT_DIR / "Gotham-Black.otf"
    FONT_MEDIUM = FONT_DIR / "Gotham-Medium.otf"
    
    MERCHANT_NAME_Y = 280
    NMID_X = 460
    NMID_Y = 350
    TERMINAL_Y = 430
    
    QR_SIZE = (650, 650)
    QR_Y_START = 510
    
    FOOTER_X = 300
    DICETAK_Y = 1465
    VERSI_Y = 1500

    def __init__(self, qris_data: str, parser: 'QRISParser'):
        self.qris_data = qris_data
        self.parser = parser

    def _load_font(self, font_path: Path, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(str(font_path), size)
        except OSError:
            return ImageFont.load_default()

    def _generate_qr_image(self, data: str, size: tuple) -> Image.Image:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert('RGB')
        return img.resize(size, Image.Resampling.LANCZOS)

    def _get_text_position(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, y: int, template_width: int) -> tuple:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (template_width - text_width) // 2
        return (x, y)

    def generate(self, output_path: str):
        if not self.TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Template not found: {self.TEMPLATE_PATH}")
        
        template = Image.open(self.TEMPLATE_PATH).convert('RGB')
        draw = ImageDraw.Draw(template)
        template_width = template.width
        
        font_name = self._load_font(self.FONT_BOLD, 44) 
        font_nmid = self._load_font(self.FONT_MEDIUM, 40)
        font_terminal = self._load_font(self.FONT_MEDIUM, 42)
        font_footer = self._load_font(self.FONT_MEDIUM, 33)
        
        merchant_name = self.parser.merchant_name.upper()
        name_pos = self._get_text_position(draw, merchant_name, font_name, self.MERCHANT_NAME_Y, template_width)
        draw.text(name_pos, merchant_name, font=font_name, fill=(0, 0, 0))
        
        nmid = self.parser.nmid
        if nmid:
            nmid_text = f"{nmid}"
            nmid_pos = (self.NMID_X, self.NMID_Y)
            draw.text(nmid_pos, nmid_text, font=font_nmid, fill=(30, 30, 30))
        
        terminal_id = self.parser.terminal_id
        if terminal_id:
            term_pos = self._get_text_position(draw, terminal_id, font_terminal, self.TERMINAL_Y, template_width)
            draw.text(term_pos, terminal_id, font=font_terminal, fill=(30, 30, 30))
        
        qr_img = self._generate_qr_image(self.qris_data, self.QR_SIZE)
        qr_x = (template_width - self.QR_SIZE[0]) // 2
        template.paste(qr_img, (qr_x, self.QR_Y_START))
        
        dicetak_id = self.parser.acquiring_id or "00000000"
        today = datetime.now().strftime("%Y.%m.%d")
        
        draw.text((self.FOOTER_X, self.DICETAK_Y), f"{dicetak_id}", font=font_footer, fill=(30, 30, 30))
        draw.text((self.FOOTER_X, self.VERSI_Y), f"1.0-{today}", font=font_footer, fill=(30, 30, 30))
        
        template = QRISParser._proc(template, self._load_font(self.FONT_BOLD, 80))
        
        template.save(output_path, 'JPEG', quality=95, subsampling=0)

def main():
    print("\n" + "="*50)
    print("        QRIS DECODER AND EDITOR")
    print("="*50)
    
    while True:
        image_path = input("\nMasukkan path gambar QRIS: ").strip()
        
        image_path = image_path.strip('"').strip("'")
        
        if not image_path:
            print("Error: Path tidak boleh kosong!")
            continue
        
        if not Path(image_path).exists():
            print(f"Error: File tidak ditemukan: {image_path}")
            continue
        
        break
    
    print("\nMembaca QR code dari gambar...")
    try:
        qris_data = QRCodeHandler.read_from_image(image_path)
        print("✓ QR code berhasil dibaca!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    parser = QRISParser(qris_data)
    parser.display_info()
    
    print("Edit Informasi Merchant:")
    print("(Tekan Enter untuk skip/tidak mengubah)\n")
    
    new_name = input(f"  Nama Merchant baru [{parser.merchant_name}]: ").strip()
    new_city = input(f"  Kota/Alamat baru [{parser.merchant_city}]: ").strip()
    new_postal = input(f"  Kode Pos baru [{parser.postal_code}]: ").strip()
    
    if not new_name and not new_city and not new_postal:
        print("\nTidak ada perubahan. Program selesai.")
        sys.exit(0)
    
    editor = QRISEditor(qris_data)
    if new_name:
        editor.set_merchant_name(new_name)
    if new_city:
        editor.set_merchant_city(new_city)
    if new_postal:
        editor.set_postal_code(new_postal)
    
    new_qris = editor.build()
    
    print("\n" + "-"*50)
    print("QRIS BARU:")
    new_parser = QRISParser(new_qris)
    new_parser.display_info()
    
    input_path = Path(image_path)
    output_path = input_path.parent / f"{input_path.stem}_edited.jpg"
    
    custom_output = ""  
    if custom_output:
        custom_output = custom_output.strip('"').strip("'")
        output_path = Path(custom_output)
    
    print("\nMembuat QR code dengan template...")
    try:
        generator = TemplateGenerator(new_qris, new_parser)
        generator.generate(str(output_path))
        print(f"QR code baru berhasil disimpan: {output_path}")
    except FileNotFoundError as e:
        print(f"Template tidak ditemukan, menggunakan QR plain...")
        QRCodeHandler.generate_qr(new_qris, str(output_path))
        print(f"QR code baru berhasil disimpan: {output_path}")
    except Exception as e:
        print(f"Error generating QR code: {e}")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("        SELESAI!")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()