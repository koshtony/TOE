import qrcode
import base64
from io import BytesIO

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")