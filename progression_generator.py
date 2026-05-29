"""
Grid Image Exporter & Progression Frame Generator
Exports grid images matching PDF rendering exactly.
Generates step-by-step coloring progression frames using solid colors.
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from colorsys import rgb_to_hsv


def export_grid_image(processed_image, palette, output_path, dpi=300, region_map=None, regions=None, label_type="borders"):
    """
    Export grid image at A4 size matching PDF exactly.
    
    If label_type="borders" (default):
        - PASS 1: Black grid lines at region boundaries only
        - PASS 1.5: Fill non-white regions with light gray (#EBEBEB)
        - PASS 2: Colored borders at region perimeters
    
    If label_type="text":
        - PASS 1: Black grid lines at region boundaries only
        - PASS 1.5: Fill non-white regions with light gray (#EBEBEB)
        - PASS 2: Text labels in region centers
    
    Args:
        processed_image: PIL Image with quantized colors
        palette: List of ColorPalette objects
        output_path: Path to save PNG
        dpi: Output DPI (default 300 for print quality)
        region_map: Optional pre-computed region map (dict mapping (x,y) → region_id)
        regions: Optional pre-computed regions dict (region_id → {'color': (r,g,b), ...})
        label_type: "borders" for colored borders (default) or "text" for text labels
    
    Returns:
        Tuple of (png_path, colors_json_path, region_map, regions)
    """
    from image_processor import ImageProcessor
    
    print(f"Exporting grid image at {dpi} DPI (A4 size)...")
    
    # A4 dimensions in pixels at target DPI
    a4_width_inches = 8.27  # 210mm
    a4_height_inches = 11.69  # 297mm
    img_width = int(a4_width_inches * dpi)
    img_height = int(a4_height_inches * dpi)
    margin_pixels = int(0.15 * dpi)  # 0.15 inch margin
    
    # Create white background image
    grid_image = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(grid_image)
    
    # Get grid data
    width, height = processed_image.size
    
    # Use provided region data or compute it
    if region_map is None or regions is None:
        processor = ImageProcessor(palette)
        region_map, regions = processor.find_regions(processed_image)
    
    print(f"DEBUG: export_grid_image - label_type={label_type}, regions={len(regions)}")
    
    # Calculate cell size to fit on A4 with minimal margins
    available_width = img_width - 2 * margin_pixels
    available_height = img_height - 2 * margin_pixels
    
    cell_width = available_width / width
    cell_height = available_height / height
    cell_size = min(cell_width, cell_height)
    
    # Calculate grid position (centered)
    grid_width = width * cell_size
    grid_height = height * cell_size
    start_x = (img_width - grid_width) / 2
    start_y = (img_height - grid_height) / 2
    
    # Create region map array for O(1) lookups
    region_map_array = np.zeros((height, width), dtype=np.int32)
    for (x, y), region_id in region_map.items():
        if 0 <= x < width and 0 <= y < height:
            region_map_array[y, x] = region_id
    
    # PASS 1: Draw black grid at region boundaries only
    print("PASS 1: Drawing black grid at boundaries...")
    line_width = max(1, int(0.1 * cell_size))  # Scale line width with cell size
    for y in range(height):
        for x in range(width):
            current_region_id = region_map_array[y, x]
            
            # Cell position
            x1 = start_x + x * cell_size
            y1 = start_y + y * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size
            
            # Draw black lines ONLY at region boundaries
            # Top edge
            if y == 0 or region_map_array[y - 1, x] != current_region_id:
                draw.line([x1, y1, x2, y1], fill=(0, 0, 0), width=line_width)
            
            # Bottom edge
            if y == height - 1 or region_map_array[y + 1, x] != current_region_id:
                draw.line([x1, y2, x2, y2], fill=(0, 0, 0), width=line_width)
            
            # Left edge
            if x == 0 or region_map_array[y, x - 1] != current_region_id:
                draw.line([x1, y1, x1, y2], fill=(0, 0, 0), width=line_width)
            
            # Right edge
            if x == width - 1 or region_map_array[y, x + 1] != current_region_id:
                draw.line([x2, y1, x2, y2], fill=(0, 0, 0), width=line_width)
    
    # PASS 1.5: Fill non-white regions with light gray (#EBEBEB) only for colored borders
    # Skip gray fill for text labels (keep all white)
    if label_type == "borders":
        print("PASS 1.5: Filling non-white regions with gray...")
        gray_color = (235, 235, 235)
        for y in range(height):
            for x in range(width):
                region_id = region_map_array[y, x]
                if region_id in regions:
                    region_color = regions[region_id]['color']
                    if region_color != (255, 255, 255):
                        # Draw filled rectangle for this cell
                        x1 = start_x + x * cell_size
                        y1 = start_y + y * cell_size
                        x2 = x1 + cell_size
                        y2 = y1 + cell_size
                        draw.rectangle([x1, y1, x2, y2], fill=gray_color, outline=None)
    else:
        print("PASS 1.5: Skipping gray fill for text labels (keeping white background)")
    
    # PASS 2: Draw labels (either colored borders or text) at region perimeters
    if label_type == "borders":
        print("PASS 2: Drawing colored borders with split-edge logic...")
        border_width = max(1, int(0.25 * cell_size))  # Scale border width with cell size (0.25 in PDF)
        offset = max(1, int(0.15 * cell_size))  # Offset for split edges (mimics PDF 0.15pt offset)
        
        for region_id, region_data in regions.items():
            color_rgb = region_data['color']
            
            # Skip white regions - leave them blank/empty
            if color_rgb == (255, 255, 255):
                continue
            
            # Find all pixels in this region
            region_pixels = np.where(region_map_array == region_id)
            y_coords, x_coords = region_pixels[0], region_pixels[1]
            
            for y, x in zip(y_coords, x_coords):
                x1 = start_x + x * cell_size
                y1 = start_y + y * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                
                # Check all 4 edges with split-edge logic (from pdf_generator.py)
                
                # TOP edge
                if y == 0 or region_map_array[y - 1, x] != region_id:
                    adjacent_region_id = region_map_array[y - 1, x] if y > 0 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        # Shared edge between two different colors: split the line
                        # Current color inside current region
                        draw.line([x1, y1 + offset, x2, y1 + offset], fill=color_rgb, width=border_width)
                        # Adjacent color inside adjacent region
                        draw.line([x1, y1 - offset, x2, y1 - offset], fill=adjacent_color, width=border_width)
                    else:
                        # Edge facing white: color on color's side, white on white's side
                        draw.line([x1, y1 + offset, x2, y1 + offset], fill=color_rgb, width=border_width)
                        draw.line([x1, y1 - offset, x2, y1 - offset], fill=(255, 255, 255), width=border_width)
                
                # BOTTOM edge
                if y == height - 1 or region_map_array[y + 1, x] != region_id:
                    adjacent_region_id = region_map_array[y + 1, x] if y < height - 1 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        # Shared edge: split the line
                        draw.line([x1, y2 - offset, x2, y2 - offset], fill=color_rgb, width=border_width)
                        draw.line([x1, y2 + offset, x2, y2 + offset], fill=adjacent_color, width=border_width)
                    else:
                        # Edge facing white
                        draw.line([x1, y2 - offset, x2, y2 - offset], fill=color_rgb, width=border_width)
                        draw.line([x1, y2 + offset, x2, y2 + offset], fill=(255, 255, 255), width=border_width)
                
                # LEFT edge
                if x == 0 or region_map_array[y, x - 1] != region_id:
                    adjacent_region_id = region_map_array[y, x - 1] if x > 0 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        # Shared edge: split the line
                        draw.line([x1 + offset, y1, x1 + offset, y2], fill=color_rgb, width=border_width)
                        draw.line([x1 - offset, y1, x1 - offset, y2], fill=adjacent_color, width=border_width)
                    else:
                        # Edge facing white
                        draw.line([x1 + offset, y1, x1 + offset, y2], fill=color_rgb, width=border_width)
                        draw.line([x1 - offset, y1, x1 - offset, y2], fill=(255, 255, 255), width=border_width)
                
                # RIGHT edge
                if x == width - 1 or region_map_array[y, x + 1] != region_id:
                    adjacent_region_id = region_map_array[y, x + 1] if x < width - 1 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        # Shared edge: split the line
                        draw.line([x2 - offset, y1, x2 - offset, y2], fill=color_rgb, width=border_width)
                        draw.line([x2 + offset, y1, x2 + offset, y2], fill=adjacent_color, width=border_width)
                    else:
                        # Edge facing white
                        draw.line([x2 - offset, y1, x2 - offset, y2], fill=color_rgb, width=border_width)
                        draw.line([x2 + offset, y1, x2 + offset, y2], fill=(255, 255, 255), width=border_width)
        
        print("PASS 2 complete: Drew colored borders\n")
    
    else:  # label_type == "text"
        print("PASS 2: Drawing text labels in regions...")
        labeled_regions = set()
        
        for region_id, region_data in regions.items():
            if region_id not in labeled_regions:
                color_rgb = region_data['color']
                
                # Skip white regions - no label needed
                if color_rgb == (255, 255, 255):
                    continue
                
                # Find label (color code) from palette
                label = None
                for palette_item in palette:
                    if palette_item.rgb == color_rgb:
                        label = palette_item.label
                        break
                
                if not label:
                    label = "?"
                
                # Find all pixels in this region
                region_pixels = np.where(region_map_array == region_id)
                y_coords, x_coords = region_pixels[0], region_pixels[1]
                
                if len(x_coords) > 0:
                    # Calculate centroid
                    cx = int(np.mean(x_coords))
                    cy = int(np.mean(y_coords))
                    
                    # Convert to image coordinates
                    text_x = int(start_x + cx * cell_size + cell_size / 2)
                    text_y = int(start_y + cy * cell_size + cell_size / 2)
                    
                    # Draw label text directly on white background (no circle)
                    text_color = (0, 0, 0)  # Black text for visibility on white
                    
                    # Use larger font for better visibility
                    try:
                        # Calculate font size based on cell size
                        font_size = max(20, int(cell_size * 0.5))
                        # Try to load a font with size (Pillow 8.0+)
                        font = ImageFont.load_default(size=font_size)
                    except TypeError:
                        # Fallback for older Pillow versions
                        try:
                            font = ImageFont.load_default()
                        except:
                            font = None
                    
                    # Get text bounding box for proper centering
                    try:
                        bbox = draw.textbbox((0, 0), label, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                    except:
                        text_width = 10
                        text_height = 10
                    
                    # Draw label centered in the region
                    label_x = text_x - text_width // 2
                    label_y = text_y - text_height // 2
                    draw.text((label_x, label_y), label, fill=text_color, font=font)
                
                labeled_regions.add(region_id)
        
        print(f"PASS 2 complete: Drew text labels for {len(labeled_regions)} regions\n")
    
    # Save PNG with DPI metadata
    grid_image.save(output_path, dpi=(dpi, dpi))
    print(f"Grid image saved: {output_path} ({img_width}×{img_height} pixels at {dpi} DPI)")
    print(f"✓ Grid includes {label_type} labels")
    
    # Create and save region_colors mapping
    region_colors = {}
    for region_id, region_data in regions.items():
        color_rgb = region_data['color']
        if color_rgb != (255, 255, 255):  # Skip white regions
            # Convert numpy types to Python native types for JSON serialization
            color_list = [int(c) for c in color_rgb]
            region_colors[int(region_id)] = color_list
    
    colors_json_path = output_path.replace('.png', '_colors.json')
    with open(colors_json_path, 'w') as f:
        json.dump(region_colors, f, indent=2)
    print(f"Region colors saved: {colors_json_path}")
    
    return output_path, colors_json_path, region_map, regions


class ProgressionGenerator:
    """Generate progression images starting from the empty grid.
    
    Each frame adds 25 more colored regions on top of the previous frame.
    Simple solid colors - no textures.
    """
    
    REGIONS_PER_FRAME = 25
    
    def __init__(self, region_map, regions, palette, width, height, dpi=300, label_type="borders", stop_event=None):
        """
        Initialize with grid information.
        
        Args:
            region_map: Dict mapping (x,y) to region_id
            regions: Dict mapping region_id to {color, size, center}
            palette: List of (r,g,b) color tuples
            width: Grid width in pixels
            height: Grid height in pixels
            dpi: Output DPI
            label_type: "borders" for colored borders, "text" for text labels
            stop_event: threading.Event() to signal cancellation (optional)
        """
        self.region_map = region_map
        self.regions = regions
        self.palette = palette
        self.width = width
        self.height = height
        self.dpi = dpi
        self.label_type = label_type  # "borders" or "text"
        self.stop_event = stop_event  # For cancellation support
        
        # Create region map array for fast lookups
        self.region_map_array = np.zeros((self.height, self.width), dtype=np.int32)
        for (x, y), region_id in self.region_map.items():
            if 0 <= x < width and 0 <= y < height:
                self.region_map_array[y, x] = region_id
        
        self.colored_regions = [
            rid for rid, rdata in regions.items() 
            if rdata['color'] != (255, 255, 255)
        ]
        
        print(f"ProgressionGenerator: {len(self.colored_regions)} colored regions, {self.REGIONS_PER_FRAME} per frame")
    
    def get_pattern_order(self, pattern_name):
        """Get regions in filling order."""
        if pattern_name == "spiral_outward":
            return self._pattern_spiral_outward()
        elif pattern_name == "top_to_bottom":
            return self._pattern_top_to_bottom()
        elif pattern_name == "left_to_right":
            return self._pattern_left_to_right()
        elif pattern_name == "smallest_first":
            return self._pattern_smallest_first()
        elif pattern_name == "color_bands":
            return self._pattern_color_bands()
        elif pattern_name == "random":
            return self._pattern_random()
        else:
            return list(self.colored_regions)
    
    def _pattern_spiral_outward(self):
        """Fill from center outward."""
        center = (self.width / 2, self.height / 2)
        def dist(rid):
            cx, cy = self.regions[rid]['center']
            return (cx - center[0])**2 + (cy - center[1])**2
        return sorted(self.colored_regions, key=dist)
    
    def _pattern_top_to_bottom(self):
        """Fill from top to bottom."""
        return sorted(self.colored_regions, key=lambda rid: self.regions[rid]['center'][1])
    
    def _pattern_left_to_right(self):
        """Fill from left to right."""
        return sorted(self.colored_regions, key=lambda rid: self.regions[rid]['center'][0])
    
    def _pattern_smallest_first(self):
        """Fill smallest regions first, largest last."""
        return sorted(self.colored_regions, key=lambda rid: self.regions[rid]['size'])
    
    def _pattern_color_bands(self):
        """Fill by color hue bands, with black filled last."""
        def hue(color):
            r, g, b = [x/255.0 for x in color]
            h, s, v = rgb_to_hsv(r, g, b)
            return h
        
        color_groups = {}
        for rid in self.colored_regions:
            color = self.regions[rid]['color']
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(rid)
        
        # Separate black from other colors (black will be filled last)
        black_group = color_groups.pop((0, 0, 0), [])
        
        # Sort non-black colors by hue
        sorted_groups = sorted(color_groups.items(), key=lambda x: hue(x[0]))
        
        result = []
        # Fill non-black colors first (smallest regions first within each color)
        for color, rids in sorted_groups:
            result.extend(sorted(rids, key=lambda rid: self.regions[rid]['size']))
        
        # Fill black regions last (smallest black regions first)
        result.extend(sorted(black_group, key=lambda rid: self.regions[rid]['size']))
        return result
    
    def _pattern_random(self):
        """Fill in random order."""
        import random
        result = list(self.colored_regions)
        random.shuffle(result)
        return result
    
    def generate_progression_frames(self, base_grid_image_path, output_dir, region_colors_path, pattern_name="spiral_outward", regions_per_frame=None, progress_callback=None):
        """
        Generate progression frames from base grid image using exact border colors.
        OPTIMIZED: Pre-caches region pixel coordinates AND keeps frames in memory!
        
        Frame 0: Base grid (unfilled)
        Frame 1: Frame 0 + N regions colored with their exact border colors
        Frame 2: Frame 1 + N more regions colored
        ... continues until all regions are colored
        
        Args:
            base_grid_image_path: Path to the base grid PNG (unfilled)
            output_dir: Directory to save progression frames
            region_colors_path: Path to JSON file with region_id → color mapping
            pattern_name: Filling pattern (spiral_outward, top_to_bottom, etc.)
            regions_per_frame: Regions to add per frame (default: self.REGIONS_PER_FRAME=25)
            progress_callback: Optional function(frame_num, total_frames, message) for GUI updates
        
        Returns:
            List of frame file paths
        """
        import sys
        
        if regions_per_frame is None:
            regions_per_frame = self.REGIONS_PER_FRAME
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Load region colors from JSON
        msg = f"Loading region colors from {region_colors_path}..."
        print(msg)
        if progress_callback:
            progress_callback(0, 1, msg)
        
        with open(region_colors_path, 'r') as f:
            region_colors = json.load(f)
        
        msg = f"✓ Loaded colors for {len(region_colors)} regions"
        print(msg)
        if progress_callback:
            progress_callback(1, 1, msg)
        
        # Load base grid image
        msg = f"Loading base grid from {base_grid_image_path}..."
        print(msg)
        if progress_callback:
            progress_callback(1, 2, msg)
        
        base_img = Image.open(base_grid_image_path).convert('RGB')
        base_array = np.array(base_img, dtype=np.uint8)
        print(f"  Base grid size: {base_img.size}\n")
        
        # Get region filling order
        region_order = self.get_pattern_order(pattern_name)
        total_regions = len(region_order)
        
        if total_regions == 0:
            print("ERROR: No colored regions!")
            return []
        
        # Calculate how many frames needed
        total_frames = (total_regions + regions_per_frame - 1) // regions_per_frame
        print(f"Generating {total_frames} frames ({total_regions} regions, {regions_per_frame}/frame)")
        print(f"Pattern: {pattern_name}")
        print(f"DPI: {self.dpi}")
        print(f"This will take a few minutes... progress shown below:\n")
        
        # PRE-CACHE: Calculate frame geometry once (not per region!)
        msg = "PRE-CALCULATING frame geometry..."
        print(msg)
        if progress_callback:
            progress_callback(1, 3, msg)
        
        a4_width_inches = 8.27
        a4_height_inches = 11.69
        img_width = int(a4_width_inches * self.dpi)
        img_height = int(a4_height_inches * self.dpi)
        margin_pixels = int(0.15 * self.dpi)
        
        available_width = img_width - 2 * margin_pixels
        available_height = img_height - 2 * margin_pixels
        
        cell_width = available_width / self.width
        cell_height = available_height / self.height
        cell_size = min(cell_width, cell_height)
        
        grid_width = self.width * cell_size
        grid_height = self.height * cell_size
        start_x = (img_width - grid_width) / 2
        start_y = (img_height - grid_height) / 2
        
        # PRE-CACHE: For each region, pre-calculate all pixel positions and coordinates
        msg = "PRE-CACHING region pixel coordinates..."
        print(msg)
        if progress_callback:
            progress_callback(2, 3, msg)
        
        region_pixel_coords = {}  # region_id → list of (py1, py2, px1, px2) tuples
        
        for idx, region_id in enumerate(region_order):
            # Find all pixels of this region
            region_pixels = self.region_map_array == region_id
            y_coords, x_coords = np.where(region_pixels)
            
            # Convert to image coordinates once and store
            pixels = []
            for y, x in zip(y_coords, x_coords):
                px1 = int(start_x + x * cell_size)
                py1 = int(start_y + y * cell_size)
                px2 = int(start_x + (x + 1) * cell_size)
                py2 = int(start_y + (y + 1) * cell_size)
                
                # Clip to image bounds
                if 0 <= py1 < img_height and 0 <= px1 < img_width:
                    py2 = min(py2, img_height)
                    px2 = min(px2, img_width)
                    pixels.append((py1, py2, px1, px2))
            
            region_pixel_coords[region_id] = pixels
        
        msg = f"✓ Pre-cached {len(region_pixel_coords)} regions\n"
        print(msg)
        if progress_callback:
            progress_callback(3, 3, msg)
        
        image_paths = []
        colored_regions = set()
        
        # Frame 0: Base grid (unfilled)
        frame_0_path = os.path.join(output_dir, "frame_0000_unfilled.png")
        base_img.save(frame_0_path, dpi=(self.dpi, self.dpi), optimize=False)
        image_paths.append(frame_0_path)
        print(f"[0/{total_frames}] Frame 0000: Unfilled grid saved")
        
        # PRE-CALCULATE ALL LABEL POSITIONS (FIXED, NOT RANDOM EACH FRAME)
        # This ensures labels stay in same position across all frames
        msg = "Pre-calculating label positions for all regions..."
        print(msg)
        if progress_callback:
            progress_callback(3, 4, msg)
        
        region_label_positions = {}  # region_id → [(image_x, image_y, label), ...]
        font_size = max(40, int(cell_size * 0.8))  # 80% of cell_size coverage
        
        try:
            label_font = ImageFont.load_default(size=font_size)
        except TypeError:
            try:
                label_font = ImageFont.load_default()
            except Exception:
                label_font = None
        
        # Pre-render a dummy label to get dimensions
        dummy_img = Image.new('RGB', (100, 100), (255, 255, 255))
        dummy_draw = ImageDraw.Draw(dummy_img)
        try:
            bbox = dummy_draw.textbbox((0, 0), "X", font=label_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width = int(font_size * 0.6)
            text_height = font_size
        
        # For each region, pre-calculate all label positions
        for region_id in self.regions.keys():
            if region_id not in self.regions:
                continue
            
            region_pixels = np.where(self.region_map_array == region_id)
            y_coords, x_coords = region_pixels[0], region_pixels[1]
            
            if len(x_coords) > 0:
                region_size = len(x_coords)
                
                # Determine number of labels based on region size (FIXED across frames)
                if region_size > 5000:
                    num_labels = 5
                elif region_size > 2000:
                    num_labels = 3
                else:
                    num_labels = 1
                
                # SELECT label indices ONCE (seed for reproducibility)
                np.random.seed(region_id)  # Use region_id as seed for deterministic random
                label_indices = np.random.choice(len(x_coords), min(num_labels, len(x_coords)), replace=False)
                np.random.seed()  # Reset seed
                
                # Convert selected pixel positions to image coordinates
                label_positions = []
                for idx in label_indices:
                    cx = x_coords[idx]
                    cy = y_coords[idx]
                    
                    # Convert to image coordinates
                    text_x = int(start_x + cx * cell_size + cell_size / 2)
                    text_y = int(start_y + cy * cell_size + cell_size / 2)
                    
                    label_positions.append((text_x, text_y))
                
                region_label_positions[region_id] = label_positions
        
        msg = f"✓ Pre-calculated positions for {len(region_label_positions)} regions\n"
        print(msg)
        if progress_callback:
            progress_callback(4, 4, msg)
        
        # OPTIMIZATION: Keep current array in memory instead of reloading from disk!
        # This is the KEY to performance - no disk I/O in the loop!
        current_array = base_array.copy()
        
        # Build label lookup (region_id → label)
        region_id_to_label = {}
        for region_id in self.regions.keys():
            region_id_str = str(region_id)
            if region_id_str not in region_colors:
                continue
            
            # Find region label by matching RGB color
            region_color_rgb = tuple(region_colors[region_id_str])
            for color_palette in self.palette:
                if color_palette.rgb == region_color_rgb:
                    region_id_to_label[region_id] = color_palette.label
                    break
        
        # Generate remaining frames
        for frame_num in range(total_frames):
            # Check if cancellation was requested
            if self.stop_event and self.stop_event.is_set():
                msg = "Frame generation cancelled by user"
                print(msg)
                if progress_callback:
                    progress_callback(frame_num, total_frames, msg)
                return image_paths  # Return frames generated so far
            
            frame_idx = frame_num + 1
            
            # Determine which regions to color in this frame
            start_idx = frame_num * regions_per_frame
            end_idx = min(start_idx + regions_per_frame, total_regions)
            new_regions = region_order[start_idx:end_idx]
            colored_regions.update(new_regions)
            
            # Color the new regions with FULL palette color (no tinting!)
            for region_id in new_regions:
                region_id_str = str(region_id)
                if region_id_str not in region_colors:
                    continue
                
                # Use full palette color for vibrant appearance
                fill_color = tuple(region_colors[region_id_str])
                
                # Use pre-cached pixel coordinates (instant lookup, no np.where!)
                for py1, py2, px1, px2 in region_pixel_coords[region_id]:
                    current_array[py1:py2, px1:px2] = fill_color
            
            # FAST: Only convert to PIL when we need to draw labels
            # Note: current_array is already uint8, so skip .astype() conversion
            current_img = Image.fromarray(current_array, 'RGB')
            draw = ImageDraw.Draw(current_img)
            
            # Draw labels ONLY for UNCOLORED regions using PRE-CALCULATED positions (FIXED!)
            uncolored_regions = set(self.regions.keys()) - colored_regions
            
            for region_id in uncolored_regions:
                if region_id not in region_id_to_label:
                    continue
                
                label = region_id_to_label[region_id]
                
                # Use PRE-CALCULATED label positions (same every frame!)
                if region_id in region_label_positions:
                    for text_x, text_y in region_label_positions[region_id]:
                        # Draw label centered at position
                        label_x = text_x - text_width // 2
                        label_y = text_y - text_height // 2
                        
                        text_color = (0, 0, 0)  # Black text for visibility
                        draw.text((label_x, label_y), label, fill=text_color, font=label_font)
            
            # Save frame with minimal PNG compression overhead (level 1 = faster, still compressed)
            filename = f"frame_{frame_idx:04d}.png"
            filepath = os.path.join(output_dir, filename)
            current_img.save(filepath, 'PNG', compress_level=1)
            image_paths.append(filepath)
            
            # Progress update
            percent_done = (frame_idx / total_frames) * 100
            msg = f"[{frame_idx}/{total_frames}] Frame {frame_idx:04d}: +{len(new_regions)} regions - {percent_done:.0f}%"
            print(msg)
            
            # Call progress callback for GUI updates
            if progress_callback:
                progress_callback(frame_idx, total_frames, msg)
            
            sys.stdout.flush()
        
        msg = f"✓ Generated {len(image_paths)} frames successfully!"
        print(msg)
        if progress_callback:
            progress_callback(total_frames, total_frames, msg)
        
        print(f"  Frames saved to: {output_dir}")
        return image_paths
