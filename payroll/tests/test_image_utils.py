import base64
import io
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

from payroll.image_utils import (
    validate_image_data_url,
    compress_and_validate_image,
    get_image_info,
    MAX_IMAGE_SIZE,
    MAX_IMAGE_DIMENSION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jpeg_data_url(width=100, height=100, color='red'):
    img = Image.new('RGB', (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"


def make_png_data_url(width=100, height=100, color='blue', mode='RGBA'):
    img = Image.new(mode, (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def make_webp_data_url(width=100, height=100):
    img = Image.new('RGB', (width, height), color='green')
    buf = io.BytesIO()
    img.save(buf, format='WEBP')
    return f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode()}"


# ---------------------------------------------------------------------------
# validate_image_data_url
# ---------------------------------------------------------------------------

class ValidateImageDataUrlTests(TestCase):

    def test_valid_jpeg(self):
        img = Image.new('RGB', (1, 1), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        img_str = base64.b64encode(buf.getvalue()).decode()
        img_type, returned_str = validate_image_data_url(f'data:image/jpeg;base64,{img_str}')
        self.assertEqual(img_type, 'image/jpeg')
        self.assertEqual(returned_str, img_str)

    def test_valid_png(self):
        result = validate_image_data_url(make_png_data_url())
        self.assertEqual(result[0], 'image/png')

    def test_valid_webp(self):
        result = validate_image_data_url(make_webp_data_url())
        self.assertEqual(result[0], 'image/webp')

    def test_gif_rejected(self):
        data_url = f"data:image/gif;base64,{base64.b64encode(b'fakegif').decode()}"
        with self.assertRaises(ValidationError) as ctx:
            validate_image_data_url(data_url)
        self.assertIn('Invalid image type', str(ctx.exception))

    def test_bmp_rejected(self):
        data_url = f"data:image/bmp;base64,{base64.b64encode(b'fakebmp').decode()}"
        with self.assertRaises(ValidationError):
            validate_image_data_url(data_url)

    def test_svg_rejected(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        data_url = f"data:image/svg+xml;base64,{base64.b64encode(svg).decode()}"
        with self.assertRaises(ValidationError):
            validate_image_data_url(data_url)

    def test_no_data_prefix_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_image_data_url('notadataurl')
        self.assertIn('Invalid image format', str(ctx.exception))

    def test_no_base64_marker_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_image_data_url('data:image/jpeg;ascii,content')
        self.assertIn('Malformed base64', str(ctx.exception))

    def test_empty_string_rejected(self):
        with self.assertRaises(ValidationError):
            validate_image_data_url('')

    def test_none_rejected(self):
        with self.assertRaises((ValidationError, AttributeError)):
            validate_image_data_url(None)


# ---------------------------------------------------------------------------
# compress_and_validate_image
# ---------------------------------------------------------------------------

class CompressAndValidateImageTests(TestCase):

    def test_compress_jpeg(self):
        result = compress_and_validate_image(make_jpeg_data_url())
        self.assertIsInstance(result, ContentFile)
        self.assertTrue(result.name.endswith('.jpg'))
        self.assertGreater(len(result.read()), 0)

    def test_compress_png_converts_to_jpeg(self):
        result = compress_and_validate_image(make_png_data_url())
        self.assertIsInstance(result, ContentFile)
        self.assertTrue(result.name.endswith('.jpg'))

    def test_compress_webp(self):
        result = compress_and_validate_image(make_webp_data_url())
        self.assertIsInstance(result, ContentFile)
        self.assertTrue(result.name.endswith('.jpg'))

    def test_rgba_png_converted_to_rgb(self):
        """PNG with transparency should be converted without errors."""
        result = compress_and_validate_image(make_png_data_url(mode='RGBA'))
        self.assertIsInstance(result, ContentFile)

    def test_la_mode_conversion(self):
        img = Image.new('LA', (50, 50), (128, 255))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        result = compress_and_validate_image(data_url)
        self.assertIsInstance(result, ContentFile)

    def test_p_mode_conversion(self):
        img = Image.new('P', (50, 50))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        result = compress_and_validate_image(data_url)
        self.assertIsInstance(result, ContentFile)

    def test_oversized_image_is_resized(self):
        large = MAX_IMAGE_DIMENSION + 200
        with patch('payroll.image_utils.logger') as mock_log:
            result = compress_and_validate_image(make_jpeg_data_url(large, large))
            mock_log.info.assert_called()
            self.assertIn('resized', str(mock_log.info.call_args).lower())
        self.assertIsInstance(result, ContentFile)

    def test_oversized_file_rejected(self):
    # Create a large base64 string that exceeds limit
        large_data = 'data:image/jpeg;base64,' + 'A' * 200000  # ~150KB
        with patch('payroll.image_utils.MAX_IMAGE_SIZE', 100):  
            with self.assertRaises(ValidationError) as ctx:
                compress_and_validate_image(large_data)
        self.assertIn('exceeds', str(ctx.exception))

    def test_invalid_base64_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            compress_and_validate_image('data:image/jpeg;base64,!!!invalid!!!')
        self.assertIn('decode', str(ctx.exception).lower())

    def test_corrupted_image_data_rejected(self):
        data_url = f"data:image/jpeg;base64,{base64.b64encode(b'notanimage').decode()}"
        with self.assertRaises(ValidationError) as ctx:
            compress_and_validate_image(data_url)
        self.assertIn('Invalid image', str(ctx.exception))

    def test_html_disguised_as_image_rejected(self):
        html = b'<html><script>alert(1)</script></html>'
        data_url = f"data:image/jpeg;base64,{base64.b64encode(html).decode()}"
        with self.assertRaises(ValidationError):
            compress_and_validate_image(data_url)

    def test_filenames_are_unique(self):
        url = make_jpeg_data_url(10, 10)
        r1 = compress_and_validate_image(url)
        r2 = compress_and_validate_image(url)
        self.assertNotEqual(r1.name, r2.name)

    @patch('payroll.image_utils.logger')
    def test_logs_success(self, mock_log):
        compress_and_validate_image(make_jpeg_data_url())
        mock_log.info.assert_called()
        self.assertIn('processed successfully', str(mock_log.info.call_args))
        
    @patch('payroll.image_utils.logger')  # Correct path
    def test_logs_error(self, mock_log):
        with self.assertRaises(ValidationError):
            compress_and_validate_image('data:image/jpeg;base64,invalid')
        mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# get_image_info
# ---------------------------------------------------------------------------

class GetImageInfoTests(TestCase):

    def test_valid_image(self):
        img = Image.new('RGB', (100, 200), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        cf = ContentFile(buf.getvalue(), name='test.jpg')
        info = get_image_info(cf)
        self.assertEqual(info['format'], 'JPEG')
        self.assertEqual(info['size'], (100, 200))
        self.assertEqual(info['mode'], 'RGB')
        self.assertGreater(info['file_size'], 0)

    def test_invalid_image_returns_empty_dict(self):
        cf = ContentFile(b'notanimage', name='fake.jpg')
        self.assertEqual(get_image_info(cf), {})

    def test_exception_returns_empty_dict(self):
        with patch('payroll.image_utils.Image.open', side_effect=IOError('fail')):
            cf = ContentFile(b'data', name='test.jpg')
            self.assertEqual(get_image_info(cf), {})

    def test_none_returns_empty_dict(self):
        self.assertEqual(get_image_info(None), {})