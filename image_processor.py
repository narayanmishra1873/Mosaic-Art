"""Ruwix algorithms."""
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from typing import List, Tuple, Dict
from config import ColorPalette

class ImageProcessor:
    def __init__(self, palette: List[ColorPalette]):
        self.palette = palette
        self.palette_rgb = np.array([c.rgb for c in palette], dtype=np.float32)
    def crop_to_viewport(self, image: Image.Image, bounds: Tuple[int, int, int, int]) -> Image.Image:
        """Crop image to viewport bounds (x1, y1, x2, y2)."""
        x1, y1, x2, y2 = bounds
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(image.width, int(x2))
        y2 = min(image.height, int(y2))
        return image.crop((x1, y1, x2, y2))
    def resize_to_grid(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        return image.resize((columns, rows), Image.Resampling.LANCZOS)
    def quantize_closest_color(self, image: Image.Image) -> Image.Image:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_arr = np.array(image, dtype=np.float32)
        h, w = img_arr.shape[:2]
        out_arr = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                pixel = img_arr[y, x]
                best_idx = min(range(len(self.palette_rgb)), key=lambda i: np.sqrt(np.sum((pixel - self.palette_rgb[i])**2)))
                out_arr[y, x] = self.palette_rgb[best_idx].astype(np.uint8)
        return Image.fromarray(out_arr, 'RGB')
    def floyd_steinberg_dither(self, image: Image.Image) -> Image.Image:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_arr = np.array(image, dtype=np.float32)
        h, w = img_arr.shape[:2]
        out_arr = np.zeros((h, w, 3), dtype=np.uint8)
        err_buf = img_arr.copy()
        for y in range(h):
            for x in range(w):
                pixel = err_buf[y, x]
                best_idx = min(range(len(self.palette_rgb)), key=lambda i: np.sqrt(np.sum((pixel - self.palette_rgb[i])**2)))
                new_color = self.palette_rgb[best_idx]
                out_arr[y, x] = new_color.astype(np.uint8)
                err = pixel - new_color
                if x + 1 < w:
                    err_buf[y, x + 1] += err * 7/16
                if x > 0 and y + 1 < h:
                    err_buf[y + 1, x - 1] += err * 3/16
                if y + 1 < h:
                    err_buf[y + 1, x] += err * 5/16
                if x + 1 < w and y + 1 < h:
                    err_buf[y + 1, x + 1] += err * 1/16
        return Image.fromarray(out_arr, 'RGB')
    def bayer_dither(self, image: Image.Image) -> Image.Image:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        bayer = np.array([[0, 0.5, 0.125, 0.625],[0.75, 0.25, 0.875, 0.375],[0.1875, 0.6875, 0.0625, 0.5625],[0.9375, 0.4375, 0.8125, 0.3125]], dtype=np.float32) - 0.5
        img_arr = np.array(image, dtype=np.float32)
        h, w = img_arr.shape[:2]
        out_arr = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                threshold = bayer[y % 4, x % 4]
                dithered = img_arr[y, x] + threshold * 255 * 0.3
                best_idx = min(range(len(self.palette_rgb)), key=lambda i: np.sqrt(np.sum((dithered - self.palette_rgb[i])**2)))
                out_arr[y, x] = self.palette_rgb[best_idx].astype(np.uint8)
        return Image.fromarray(out_arr, 'RGB')
    def _bayer_dither_custom(self, image: Image.Image, threshold_mult: float = 0.3) -> Image.Image:
        """Bayer dither with customizable threshold multiplier."""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        bayer = np.array([[0, 0.5, 0.125, 0.625],[0.75, 0.25, 0.875, 0.375],[0.1875, 0.6875, 0.0625, 0.5625],[0.9375, 0.4375, 0.8125, 0.3125]], dtype=np.float32) - 0.5
        img_arr = np.array(image, dtype=np.float32)
        h, w = img_arr.shape[:2]
        out_arr = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                threshold = bayer[y % 4, x % 4]
                dithered = img_arr[y, x] + threshold * 255 * threshold_mult
                best_idx = min(range(len(self.palette_rgb)), key=lambda i: np.sqrt(np.sum((dithered - self.palette_rgb[i])**2)))
                out_arr[y, x] = self.palette_rgb[best_idx].astype(np.uint8)
        return Image.fromarray(out_arr, 'RGB')
    def method_1_diffusion_smooth(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Floyd-Steinberg: Smooth (median blur + moderate contrast for continuous segments)."""
        # Median filter to smooth out noise and merge similar colors
        smoothed = image.filter(ImageFilter.MedianFilter(size=3))
        # Moderate contrast enhancement (less than contrast version)
        contrasted = ImageEnhance.Contrast(smoothed).enhance(1.2)
        resized = self.resize_to_grid(contrasted, rows, columns)
        return self.floyd_steinberg_dither(resized)
    def method_2_diffusion_vibrant(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Floyd-Steinberg: Vibrant (2.0x color saturation)."""
        enhanced = ImageEnhance.Color(image).enhance(2.0)
        return self.floyd_steinberg_dither(self.resize_to_grid(enhanced, rows, columns))
    def method_3_diffusion_sharp(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Superpixel Sharp: Median (size 5) + max contrast + aggressive sharpening to reduce confetti while preserving detail."""
        # Light median filter for color merging (preserves more detail than larger sizes)
        smoothed = image.filter(ImageFilter.MedianFilter(size=5))
        # Strong contrast to collapse similar colors into fewer unique values
        contrasted = ImageEnhance.Contrast(smoothed).enhance(2.2)
        # Aggressive sharpening to preserve edges and reduce confetti artifacts
        # High percent value (300) creates crisp boundaries between color regions
        sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=2, percent=300))
        return self.floyd_steinberg_dither(self.resize_to_grid(sharpened, rows, columns))
    def method_4_diffusion_bright(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Superpixel: Large median filter (size 9) merges adjacent pixels + strong contrast reduction."""
        # Aggressive median filter to merge similar adjacent colors (superpixel effect)
        # Size 9 creates visible superpixel blocks, reducing coloring cells from ~20k to ~5k
        smoothed = image.filter(ImageFilter.MedianFilter(size=9))
        # Strong contrast enhancement to reduce unique colors
        contrasted = ImageEnhance.Contrast(smoothed).enhance(2.0)
        # Light sharpening to define superpixel blocks
        sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1, percent=100))
        return self.floyd_steinberg_dither(self.resize_to_grid(sharpened, rows, columns))
    def method_5_diffusion_contrast(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Floyd-Steinberg: High Contrast (1.5x contrast + sharpening)."""
        contrast_enhanced = ImageEnhance.Contrast(image).enhance(1.5)
        sharpened = contrast_enhanced.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150))
        return self.floyd_steinberg_dither(self.resize_to_grid(sharpened, rows, columns))
    def method_6_bayer_standard(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Bayer: Standard (no preprocessing)."""
        return self.bayer_dither(self.resize_to_grid(image, rows, columns))
    def method_7_bayer_aggressive(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Bayer: Aggressive (stronger dithering effect with 0.5x threshold multiplier)."""
        resized = self.resize_to_grid(image, rows, columns)
        return self._bayer_dither_custom(resized, threshold_mult=0.5)
    def method_8_bayer_vibrant(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Bayer: Vibrant (2.2x color saturation + dithering)."""
        enhanced = ImageEnhance.Color(image).enhance(2.2)
        return self.bayer_dither(self.resize_to_grid(enhanced, rows, columns))
    def method_9_bayer_crisp(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Bayer: Crisp (sharpening + reduced dithering for clean output)."""
        sharpened = image.filter(ImageFilter.UnsharpMask(radius=2.5, percent=300))
        resized = self.resize_to_grid(sharpened, rows, columns)
        return self._bayer_dither_custom(resized, threshold_mult=0.15)
    def method_10_bw_simple(self, image: Image.Image, rows: int, columns: int) -> Image.Image:
        """Stencil Mode: Black outline-only (user fills with any medium - pencil, watercolor, marker)."""
        # Convert to grayscale and resize
        gray = image.convert('L')
        resized = gray.resize((columns, rows), Image.Resampling.LANCZOS)
        
        # Blur to smooth and reduce noise
        blurred = resized.filter(ImageFilter.GaussianBlur(radius=1.5))
        
        # Detect edges - FIND_EDGES produces bright values at edges
        edges = blurred.filter(ImageFilter.FIND_EDGES)
        
        # Threshold to isolate strong edges
        arr = np.array(edges, dtype=np.uint8)
        # FIND_EDGES: high values = edges, low values = smooth areas
        # Create binary: 1 at edges, 0 at non-edges
        edge_binary = (arr > 50).astype(np.uint8)
        
        # Dilate edges to make them thicker and more visible (maximum filter)
        dilated = np.zeros_like(edge_binary)
        for y in range(1, edge_binary.shape[0] - 1):
            for x in range(1, edge_binary.shape[1] - 1):
                # Take maximum in 3x3 neighborhood to expand edges
                dilated[y, x] = np.max(edge_binary[y-1:y+2, x-1:x+2])
        
        # Convert to output: 1 (edge) -> 0 (black), 0 (non-edge) -> 255 (white)
        stencil = np.where(dilated == 1, 0, 255).astype(np.uint8)
        
        # Create RGB output (outline only, no colors or labels)
        rgb_arr = np.stack([stencil] * 3, axis=-1)
        return Image.fromarray(rgb_arr, 'RGB')
    
    def find_regions(self, image: Image.Image) -> Tuple[Dict, Dict]:
        """
        Find contiguous regions of same color using flood fill.
        
        Returns:
            - region_map: Dict[(x, y)] -> region_id
            - regions: Dict[region_id] -> {color: RGB, center: (cx, cy), size: count}
        
        Time Complexity: O(W*H)
        """
        from collections import deque
        
        img_array = np.array(image, dtype=np.uint8)
        if len(img_array.shape) == 2:  # Grayscale
            img_array = np.stack([img_array] * 3, axis=-1)
        
        h, w = img_array.shape[:2]
        visited = set()
        region_map = {}
        regions = {}
        region_id = 0
        
        def get_color_key(x, y):
            """Get color tuple for pixel."""
            return tuple(img_array[y, x])
        
        def bfs(start_x, start_y):
            """BFS to find all pixels in region."""
            nonlocal region_id
            
            color = get_color_key(start_x, start_y)
            queue = deque([(start_x, start_y)])
            visited.add((start_x, start_y))
            pixels = [(start_x, start_y)]
            
            while queue:
                x, y = queue.popleft()
                region_map[(x, y)] = region_id
                
                # Check 4 neighbors (up, down, left, right)
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        if get_color_key(nx, ny) == color:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
                            pixels.append((nx, ny))
            
            # Calculate centroid
            cx = sum(p[0] for p in pixels) // len(pixels)
            cy = sum(p[1] for p in pixels) // len(pixels)
            
            regions[region_id] = {
                'color': color,
                'center': (cx, cy),
                'size': len(pixels)
            }
            region_id += 1
        
        # Scan all pixels
        for y in range(h):
            for x in range(w):
                if (x, y) not in visited:
                    bfs(x, y)
        
        return region_map, regions
    
    def get_all_algorithms(self) -> Dict[str, Tuple[str, callable]]:
        return {
            "1": ("1. Diffusion Smooth", self.method_1_diffusion_smooth),
            "2": ("2. Diffusion Vibrant", self.method_2_diffusion_vibrant),
            "3": ("3. Superpixel Sharp", self.method_3_diffusion_sharp),
            "4": ("4. Diffusion Superpixel", self.method_4_diffusion_bright),
            "5": ("5. Diffusion Contrast", self.method_5_diffusion_contrast),
            "6": ("6. Bayer Standard", self.method_6_bayer_standard),
            "7": ("7. Bayer Aggressive", self.method_7_bayer_aggressive),
            "8": ("8. Bayer Vibrant", self.method_8_bayer_vibrant),
            "9": ("9. Bayer Crisp", self.method_9_bayer_crisp),
            "10": ("10. Stencil Mode", self.method_10_bw_simple),
        }
