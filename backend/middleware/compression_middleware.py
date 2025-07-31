# backend/middleware/compression_middleware.py
"""
TeleBoost Compression Middleware
High-performance response compression with gzip and brotli
"""
import gzip
import logging
from io import BytesIO
from typing import Set, Optional, Tuple
from flask import Flask, request, Response

try:
    import brotli

    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    logging.warning("Brotli not available, using gzip only")

logger = logging.getLogger(__name__)


class CompressionMiddleware:
    """
    Response compression middleware with:
    - Brotli compression (best compression ratio)
    - Gzip fallback
    - Content-type filtering
    - Size threshold
    - Quality settings based on content type
    """

    # Minimum size for compression (bytes)
    MIN_SIZE = 1024  # 1KB

    # Content types to compress
    COMPRESSIBLE_TYPES = {
        'text/html',
        'text/css',
        'text/xml',
        'text/plain',
        'text/javascript',
        'application/javascript',
        'application/json',
        'application/xml',
        'application/rss+xml',
        'application/atom+xml',
        'application/xhtml+xml',
        'application/x-font-ttf',
        'application/x-font-opentype',
        'application/vnd.ms-fontobject',
        'image/svg+xml',
        'image/x-icon',
    }

    # Content types that should never be compressed
    INCOMPRESSIBLE_TYPES = {
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'video/mp4',
        'video/webm',
        'audio/mpeg',
        'audio/ogg',
        'application/zip',
        'application/gzip',
        'application/x-gzip',
        'application/x-bzip2',
        'application/x-7z-compressed',
    }

    def __init__(self, app: Flask):
        """Initialize compression middleware"""
        self.app = app

        # Compression settings
        self.gzip_level = 6  # 1-9, 6 is good balance
        self.brotli_quality = 4  # 0-11, 4 is good for dynamic content

        # Statistics
        self.stats = {
            'total_compressed': 0,
            'bytes_saved': 0,
            'brotli_used': 0,
            'gzip_used': 0,
        }

        # Register after_request handler
        app.after_request(self._compress_response)

        logger.info(f"Compression middleware initialized (Brotli: {BROTLI_AVAILABLE})")

    def _compress_response(self, response: Response) -> Response:
        """
        Compress response if applicable

        Args:
            response: Flask response object

        Returns:
            Compressed or original response
        """
        # Skip compression for certain conditions
        if not self._should_compress(response):
            return response

        # Get accepted encodings
        accept_encoding = request.headers.get('Accept-Encoding', '')

        # Get response data
        data = response.get_data()
        original_size = len(data)

        # Try Brotli first (better compression)
        if BROTLI_AVAILABLE and 'br' in accept_encoding:
            compressed_data = self._brotli_compress(data)
            encoding = 'br'
            self.stats['brotli_used'] += 1
        # Fall back to gzip
        elif 'gzip' in accept_encoding:
            compressed_data = self._gzip_compress(data)
            encoding = 'gzip'
            self.stats['gzip_used'] += 1
        else:
            # Client doesn't support compression
            return response

        # Check if compression actually saved space
        compressed_size = len(compressed_data)
        if compressed_size >= original_size * 0.9:  # Less than 10% savings
            return response

        # Update response with compressed data
        response.set_data(compressed_data)

        # Set compression headers
        response.headers['Content-Encoding'] = encoding
        response.headers['Content-Length'] = str(compressed_size)

        # Add Vary header to indicate response varies by Accept-Encoding
        vary = response.headers.get('Vary', '')
        if vary:
            if 'Accept-Encoding' not in vary:
                response.headers['Vary'] = f"{vary}, Accept-Encoding"
        else:
            response.headers['Vary'] = 'Accept-Encoding'

        # Update statistics
        self.stats['total_compressed'] += 1
        self.stats['bytes_saved'] += (original_size - compressed_size)

        # Log compression ratio for debugging
        ratio = (1 - compressed_size / original_size) * 100
        logger.debug(
            f"Compressed response: {original_size} → {compressed_size} bytes "
            f"({ratio:.1f}% reduction) using {encoding}"
        )

        return response

    def _should_compress(self, response: Response) -> bool:
        """
        Determine if response should be compressed

        Args:
            response: Flask response object

        Returns:
            True if should compress, False otherwise
        """
        # Don't compress if already encoded
        if 'Content-Encoding' in response.headers:
            return False

        # Check status code (only compress successful responses)
        if response.status_code < 200 or response.status_code >= 300:
            return False

        # Check content type
        content_type = response.content_type
        if not content_type:
            return False

        # Extract base content type (without charset)
        base_type = content_type.split(';')[0].strip().lower()

        # Never compress incompressible types
        if base_type in self.INCOMPRESSIBLE_TYPES:
            return False

        # Check if type is compressible
        if base_type not in self.COMPRESSIBLE_TYPES:
            # Also check for partial matches (e.g., application/json+ld)
            compressible = any(
                ct in base_type for ct in ['json', 'xml', 'text', 'javascript']
            )
            if not compressible:
                return False

        # Check size threshold
        content_length = response.content_length
        if content_length is not None and content_length < self.MIN_SIZE:
            return False

        # If no content length, check actual data size
        if content_length is None:
            data_size = len(response.get_data())
            if data_size < self.MIN_SIZE:
                return False

        return True

    def _gzip_compress(self, data: bytes) -> bytes:
        """
        Compress data using gzip

        Args:
            data: Data to compress

        Returns:
            Compressed data
        """
        buffer = BytesIO()
        with gzip.GzipFile(
                mode='wb',
                compresslevel=self.gzip_level,
                fileobj=buffer
        ) as gz:
            gz.write(data)
        return buffer.getvalue()

    def _brotli_compress(self, data: bytes) -> bytes:
        """
        Compress data using Brotli

        Args:
            data: Data to compress

        Returns:
            Compressed data
        """
        return brotli.compress(
            data,
            quality=self.brotli_quality,
            mode=brotli.MODE_TEXT  # Optimize for text
        )

    def get_compression_stats(self) -> dict:
        """Get compression statistics"""
        stats = self.stats.copy()

        # Calculate average compression ratio
        if stats['total_compressed'] > 0:
            stats['average_savings_mb'] = round(
                stats['bytes_saved'] / (1024 * 1024), 2
            )
        else:
            stats['average_savings_mb'] = 0

        stats['brotli_available'] = BROTLI_AVAILABLE

        return stats

    def reset_stats(self) -> None:
        """Reset compression statistics"""
        self.stats = {
            'total_compressed': 0,
            'bytes_saved': 0,
            'brotli_used': 0,
            'gzip_used': 0,
        }