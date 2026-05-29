"""
PDF generation module for creating printable color-by-numbers grids.
"""

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from typing import List, Tuple
from config import ColorPalette, PDF_MARGIN
import numpy as np
import tempfile
import os


class PDFGenerator:
    """Handles PDF generation for color-by-numbers grids."""
    
    def __init__(self, processed_image: Image.Image, palette: List[ColorPalette]):
        """
        Initialize PDF generator.
        
        Args:
            processed_image: PIL Image with grid data (each pixel is a palette color)
            palette: List of ColorPalette objects
        """
        self.processed_image = processed_image
        self.palette = palette
        self.palette_rgb = {tuple(color.rgb): color.label for color in palette}
        
        # A4 dimensions in points
        self.page_width, self.page_height = A4
        self.margin = PDF_MARGIN * inch
    
    def calculate_grid_dimensions(self) -> Tuple[float, float, float, float]:
        """
        Calculate the optimal grid size to fit on A4 page while maximizing cell size.
        
        Returns:
            Tuple of (cell_size, grid_width, grid_height, start_x, start_y)
        """
        grid_width_pixels, grid_height_pixels = self.processed_image.size
        
        # Available space on page
        available_width = self.page_width - 2 * self.margin
        available_height = self.page_height - 2 * self.margin
        
        # Calculate cell size (same for both dimensions for square cells)
        cell_size_by_width = available_width / grid_width_pixels
        cell_size_by_height = available_height / grid_height_pixels
        cell_size = min(cell_size_by_width, cell_size_by_height)
        
        # Calculate total grid dimensions
        grid_width = grid_width_pixels * cell_size
        grid_height = grid_height_pixels * cell_size
        
        # Center the grid on the page
        start_x = (self.page_width - grid_width) / 2
        start_y = (self.page_height - grid_height) / 2
        
        return cell_size, grid_width, grid_height, start_x, start_y
    
    def get_pixel_label(self, rgb: Tuple[int, int, int]) -> str:
        """
        Get the palette label for an RGB color.
        
        Args:
            rgb: Tuple of (R, G, B) values
            
        Returns:
            Single-letter label
        """
        # Try exact match first
        if rgb in self.palette_rgb:
            return self.palette_rgb[rgb]
        
        # Find closest color in palette if exact match not found
        min_distance = float('inf')
        closest_label = self.palette[0].label
        
        for color in self.palette:
            distance = sum((a - b) ** 2 for a, b in zip(rgb, color.rgb)) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_label = color.label
        
        return closest_label
    
    def generate_pdf(self, output_path: str, merged_regions: bool = False, use_borders: bool = False) -> None:
        """
        Generate and save a 2-page PDF file.
        Page 1: Grid with thin lines and color labels (or colored borders)
        Page 2: Final processed image as reference
        
        Args:
            output_path: Path to save the PDF file
            merged_regions: If True, merge contiguous same-color regions
            use_borders: If True, draw colored borders instead of text labels (only in merged mode)
        """
        # Create canvas
        pdf_canvas = canvas.Canvas(output_path, pagesize=A4)
        
        # ============ PAGE 1: GRID WITH LABELS ============
        if merged_regions:
            if use_borders:
                self._draw_grid_page_merged_borders(pdf_canvas)
            else:
                self._draw_grid_page_merged(pdf_canvas)
        else:
            self._draw_grid_page(pdf_canvas)
        
        # ============ PAGE 2: REFERENCE IMAGE ============
        pdf_canvas.showPage()
        self._draw_image_page(pdf_canvas)
        
        # Save PDF
        pdf_canvas.save()
    
    def _draw_grid_page(self, pdf_canvas) -> None:
        """
        Draw page 1: Grid with thin lines and centered letter labels.
        """
        # Calculate grid dimensions
        cell_size, grid_width, grid_height, start_x, start_y = self.calculate_grid_dimensions()
        
        # Get image data
        image_array = np.array(self.processed_image, dtype=np.uint8)
        height, width = image_array.shape[:2]
        
        # Draw grid and labels with thin lines
        pdf_canvas.setLineWidth(0.1)  # Ultra-thin lines
        
        # Set gray color for text (stick letters style)
        from reportlab.lib.colors import HexColor
        text_color = HexColor("#808080")  # Medium gray, visible but faint for sketchpen
        
        for row in range(height):
            for col in range(width):
                # Calculate cell position
                x = start_x + col * cell_size
                y = start_y + (height - row - 1) * cell_size  # Flip y-axis for PDF
                
                # Draw cell border (thin)
                pdf_canvas.rect(x, y, cell_size, cell_size, stroke=1, fill=0)
                
                # Get pixel color and label
                if len(image_array.shape) == 3:
                    pixel_rgb = tuple(image_array[row, col])
                else:
                    # Grayscale - convert to RGB
                    gray = image_array[row, col]
                    pixel_rgb = (gray, gray, gray)
                
                label = self.get_pixel_label(pixel_rgb)
                
                # Skip white pixels (leave empty for paper color)
                if pixel_rgb == (255, 255, 255):
                    continue
                
                # Calculate text position (center of cell with proper margins)
                text_x = x + cell_size / 2
                # Use smaller font (20% of cell_size) for thinner appearance matching grid lines
                font_size = max(4, int(cell_size * 0.1))
                # Adjust vertical position: move text down more to create clearance from top line
                text_y = y + cell_size / 2 - (font_size * 0.35)
                
                # Draw label text (using Helvetica for thin letters matching 0.1 line weight)
                pdf_canvas.setFont("Helvetica", font_size)
                pdf_canvas.setFillColor(text_color)
                pdf_canvas.drawCentredString(text_x, text_y, label)
    
    def _draw_grid_page_merged(self, pdf_canvas) -> None:
        """
        Draw page 1 with merged regions: shared borders erased for same-color pixels.
        Time Complexity: O(W*H)
        """
        # Find regions using efficient flood fill
        from image_processor import ImageProcessor
        processor = ImageProcessor(self.palette)
        region_map, regions = processor.find_regions(self.processed_image)
        
        # Calculate grid dimensions
        cell_size, grid_width, grid_height, start_x, start_y = self.calculate_grid_dimensions()
        
        # Get image data
        image_array = np.array(self.processed_image, dtype=np.uint8)
        height, width = image_array.shape[:2]
        
        # Draw grid with smart borders (only where colors differ)
        pdf_canvas.setLineWidth(0.1)  # Ultra-thin lines
        
        from reportlab.lib.colors import HexColor
        text_color = HexColor("#808080")  # Medium gray
        
        labeled_regions = set()  # Track which regions we've labeled
        
        for row in range(height):
            for col in range(width):
                x = start_x + col * cell_size
                y = start_y + (height - row - 1) * cell_size
                
                current_region_id = region_map.get((col, row))
                
                # Draw borders only at region boundaries
                # Top border
                if row == 0 or region_map.get((col, row - 1)) != current_region_id:
                    pdf_canvas.line(x, y + cell_size, x + cell_size, y + cell_size)
                
                # Bottom border
                if row == height - 1 or region_map.get((col, row + 1)) != current_region_id:
                    pdf_canvas.line(x, y, x + cell_size, y)
                
                # Left border
                if col == 0 or region_map.get((col - 1, row)) != current_region_id:
                    pdf_canvas.line(x, y, x, y + cell_size)
                
                # Right border
                if col == width - 1 or region_map.get((col + 1, row)) != current_region_id:
                    pdf_canvas.line(x + cell_size, y, x + cell_size, y + cell_size)
        
        # Label each region - multiple labels for large regions based on size
        MAX_PIXELS_PER_LABEL = 500  # One label per 500 pixels (adjust for label density)
        
        for region_id, region_data in regions.items():
            if region_id not in labeled_regions:
                color_rgb = region_data['color']
                
                # Skip white regions (leave empty for paper color) - check exact white (255,255,255)
                if color_rgb == (255, 255, 255):
                    continue
                
                label = self.get_pixel_label(color_rgb)
                
                # Find all pixels in this region
                region_pixels = [pos for pos, rid in region_map.items() if rid == region_id]
                
                if not region_pixels:
                    continue
                
                # Calculate how many labels needed for this region
                num_labels = max(1, len(region_pixels) // MAX_PIXELS_PER_LABEL)
                
                # Place labels distributed throughout the region
                for label_idx in range(num_labels):
                    # Divide pixels into groups
                    start_idx = (label_idx * len(region_pixels)) // num_labels
                    end_idx = ((label_idx + 1) * len(region_pixels)) // num_labels
                    label_group = region_pixels[start_idx:end_idx]
                    
                    # Find centroid of this group
                    group_cx = sum(p[0] for p in label_group) / len(label_group)
                    group_cy = sum(p[1] for p in label_group) / len(label_group)
                    
                    # Find closest pixel to group centroid
                    closest_pixel = min(
                        label_group,
                        key=lambda p: (p[0] - group_cx) ** 2 + (p[1] - group_cy) ** 2
                    )
                    label_x, label_y = closest_pixel
                    
                    # Convert pixel coordinates to PDF coordinates
                    pdf_x = start_x + label_x * cell_size + cell_size / 2
                    pdf_y = start_y + (height - label_y - 1) * cell_size + cell_size / 2
                    
                    # Larger font for regions (20% of cell_size)
                    font_size = max(6, int(cell_size * 0.25))
                    
                    pdf_canvas.setFont("Helvetica-Bold", font_size)
                    pdf_canvas.setFillColor(text_color)
                    pdf_canvas.drawCentredString(pdf_x, pdf_y - (font_size * 0.35), label)
                
                labeled_regions.add(region_id)
    
    def _draw_grid_page_merged_borders(self, pdf_canvas) -> None:
        """
        Draw page 1 with merged regions: black grid + colored region-boundary borders.
        For shared edges between different colors: split line showing both colors (half thickness each).
        For edges facing white: full color line.
        White regions remain empty (no colored marking).
        """
        # Find regions using efficient flood fill
        from image_processor import ImageProcessor
        processor = ImageProcessor(self.palette)
        region_map, regions = processor.find_regions(self.processed_image)
        
        # Calculate grid dimensions
        cell_size, grid_width, grid_height, start_x, start_y = self.calculate_grid_dimensions()
        
        # Get image data
        image_array = np.array(self.processed_image, dtype=np.uint8)
        height, width = image_array.shape[:2]
        
        from reportlab.lib.colors import HexColor
        
        # PASS 1: Draw black grid lines (region boundaries only)
        pdf_canvas.setLineWidth(0.1)
        pdf_canvas.setStrokeColor(HexColor("#000000"))
        
        for row in range(height):
            for col in range(width):
                x = start_x + col * cell_size
                y = start_y + (height - row - 1) * cell_size
                
                current_region_id = region_map.get((col, row))
                
                # Draw black grid ONLY at region boundaries
                # Top border
                if row == 0 or region_map.get((col, row - 1)) != current_region_id:
                    pdf_canvas.line(x, y + cell_size, x + cell_size, y + cell_size)
                
                # Bottom border
                if row == height - 1 or region_map.get((col, row + 1)) != current_region_id:
                    pdf_canvas.line(x, y, x + cell_size, y)
                
                # Left border
                if col == 0 or region_map.get((col - 1, row)) != current_region_id:
                    pdf_canvas.line(x, y, x, y + cell_size)
                
                # Right border
                if col == width - 1 or region_map.get((col + 1, row)) != current_region_id:
                    pdf_canvas.line(x + cell_size, y, x + cell_size, y + cell_size)
        
        # PASS 1.5: Fill non-white regions with light gray background
        from reportlab.lib.colors import HexColor
        pdf_canvas.setFillColor(HexColor("#EBEBEB"))
        pdf_canvas.setLineWidth(0)  # No outline for fill
        
        for row in range(height):
            for col in range(width):
                current_region_id = region_map.get((col, row))
                current_color = regions[current_region_id]['color'] if current_region_id in regions else None
                
                # Fill non-white regions with light gray
                if current_color != (255, 255, 255):
                    x = start_x + col * cell_size
                    y = start_y + (height - row - 1) * cell_size
                    pdf_canvas.rect(x, y, cell_size, cell_size, fill=1, stroke=0)
        
        # PASS 2: Draw colored strokes at region boundaries
        # For shared edges between colors: split the line (both colors visible)
        # For edges facing white: full colored line
        pdf_canvas.setLineWidth(0.5)  # Base thickness
        
        for region_id, region_data in regions.items():
            color_rgb = region_data['color']
            
            # Skip white regions - leave them blank/empty
            if color_rgb == (255, 255, 255):
                continue
            
            # Convert RGB to hex for reportlab - use ACTUAL color for borders
            r, g, b = color_rgb
            # Use actual region color for borders so they're visible
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            
            # Find all pixels in this region
            region_pixels = [pos for pos, rid in region_map.items() if rid == region_id]
            
            if not region_pixels:
                continue
            
            # Draw colored strokes at region perimeter
            for px, py in region_pixels:
                x = start_x + px * cell_size
                y = start_y + (height - py - 1) * cell_size
                
                # Check all 4 edges
                # TOP edge
                if py == 0 or region_map.get((px, py - 1)) != region_id:
                    adjacent_region_id = region_map.get((px, py - 1)) if py > 0 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id and adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        # Shared edge: current color draws inside this region, adjacent color draws inside its region
                        pdf_canvas.setLineWidth(0.25)
                        # Current color (below adjacent): draw at bottom of this edge
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x, y + cell_size - 0.15, x + cell_size, y + cell_size - 0.15)
                        
                        # Adjacent color (above this region): draw at top of this edge
                        ar, ag, ab = adjacent_color
                        adj_hex = f"#{ar:02x}{ag:02x}{ab:02x}"
                        pdf_canvas.setStrokeColor(HexColor(adj_hex))
                        pdf_canvas.line(x, y + cell_size + 0.15, x + cell_size, y + cell_size + 0.15)
                    else:
                        # Edge facing white: color on color's side, white on white's side
                        pdf_canvas.setLineWidth(0.25)
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x, y + cell_size - 0.15, x + cell_size, y + cell_size - 0.15)
                        # White side
                        pdf_canvas.setStrokeColor(HexColor("#FFFFFF"))
                        pdf_canvas.line(x, y + cell_size + 0.15, x + cell_size, y + cell_size + 0.15)
                
                
                # BOTTOM edge
                if py == height - 1 or region_map.get((px, py + 1)) != region_id:
                    adjacent_region_id = region_map.get((px, py + 1)) if py < height - 1 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id and adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        pdf_canvas.setLineWidth(0.25)
                        # Current color (above adjacent): draw at top of this edge
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x, y + 0.15, x + cell_size, y + 0.15)
                        
                        # Adjacent color (below this region): draw at bottom of this edge
                        ar, ag, ab = adjacent_color
                        adj_hex = f"#{ar:02x}{ag:02x}{ab:02x}"
                        pdf_canvas.setStrokeColor(HexColor(adj_hex))
                        pdf_canvas.line(x, y - 0.15, x + cell_size, y - 0.15)
                    else:
                        # Edge facing white: color on color's side, white on white's side
                        pdf_canvas.setLineWidth(0.25)
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x, y + 0.15, x + cell_size, y + 0.15)
                        # White side
                        pdf_canvas.setStrokeColor(HexColor("#FFFFFF"))
                        pdf_canvas.line(x, y - 0.15, x + cell_size, y - 0.15)
                
                # LEFT edge
                if px == 0 or region_map.get((px - 1, py)) != region_id:
                    adjacent_region_id = region_map.get((px - 1, py)) if px > 0 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id and adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        pdf_canvas.setLineWidth(0.25)
                        # Current color (right side): draw inside current region, to the right
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x + 0.15, y, x + 0.15, y + cell_size)
                        
                        # Adjacent color (left side): draw inside adjacent region, to the left
                        ar, ag, ab = adjacent_color
                        adj_hex = f"#{ar:02x}{ag:02x}{ab:02x}"
                        pdf_canvas.setStrokeColor(HexColor(adj_hex))
                        pdf_canvas.line(x - 0.15, y, x - 0.15, y + cell_size)
                    else:
                        # Edge facing white: color on color's side, white on white's side
                        pdf_canvas.setLineWidth(0.25)
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x + 0.15, y, x + 0.15, y + cell_size)
                        # White side
                        pdf_canvas.setStrokeColor(HexColor("#FFFFFF"))
                        pdf_canvas.line(x - 0.15, y, x - 0.15, y + cell_size)
                
                # RIGHT edge
                if px == width - 1 or region_map.get((px + 1, py)) != region_id:
                    adjacent_region_id = region_map.get((px + 1, py)) if px < width - 1 else None
                    adjacent_color = regions[adjacent_region_id]['color'] if adjacent_region_id and adjacent_region_id in regions else (255, 255, 255)
                    
                    if adjacent_color != (255, 255, 255) and adjacent_color != color_rgb:
                        pdf_canvas.setLineWidth(0.25)
                        # Current color (left side): draw inside current region, to the left
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x + cell_size - 0.15, y, x + cell_size - 0.15, y + cell_size)
                        
                        # Adjacent color (right side): draw inside adjacent region, to the right
                        ar, ag, ab = adjacent_color
                        adj_hex = f"#{ar:02x}{ag:02x}{ab:02x}"
                        pdf_canvas.setStrokeColor(HexColor(adj_hex))
                        pdf_canvas.line(x + cell_size + 0.15, y, x + cell_size + 0.15, y + cell_size)
                    else:
                        # Edge facing white: color on color's side, white on white's side
                        pdf_canvas.setLineWidth(0.25)
                        pdf_canvas.setStrokeColor(HexColor(color_hex))
                        pdf_canvas.line(x + cell_size - 0.15, y, x + cell_size - 0.15, y + cell_size)
                        # White side
                        pdf_canvas.setStrokeColor(HexColor("#FFFFFF"))
                        pdf_canvas.line(x + cell_size + 0.15, y, x + cell_size + 0.15, y + cell_size)
    
    def _draw_image_page(self, pdf_canvas) -> None:
        """
        Draw page 2: Final processed image as reference/color guide.
        """
        # Add title
        pdf_canvas.setFont("Helvetica-Bold", 14)
        pdf_canvas.drawString(self.margin, self.page_height - self.margin - 20, 
                             "Color Reference Image")
        
        # Calculate image dimensions to fit on page
        available_width = self.page_width - 2 * self.margin
        available_height = self.page_height - 2 * self.margin - 40  # Space for title
        
        # Scale image to fit
        img_aspect = self.processed_image.width / self.processed_image.height
        page_aspect = available_width / available_height
        
        if img_aspect > page_aspect:
            # Image is wider - limit by width
            display_width = available_width
            display_height = display_width / img_aspect
        else:
            # Image is taller - limit by height
            display_height = available_height
            display_width = display_height * img_aspect
        
        # Center image on page
        img_x = (self.page_width - display_width) / 2
        img_y = self.page_height - self.margin - 40 - display_height
        
        # Save processed image temporarily for embedding
        temp_dir = tempfile.gettempdir()
        temp_image_path = os.path.join(temp_dir, "temp_mosaic_ref.png")
        self.processed_image.save(temp_image_path)
        
        try:
            # Draw image on PDF with explicit width and height parameters
            pdf_canvas.drawImage(temp_image_path, img_x, img_y, display_width, display_height)
        except Exception as e:
            pdf_canvas.drawString(self.margin, img_y + 20, f"Error embedding image: {str(e)}")
        finally:
            # Clean up temp file
            try:
                os.remove(temp_image_path)
            except:
                pass
        
        # Add color palette legend
        self._draw_palette_legend(pdf_canvas)
    
    def _draw_palette_legend(self, pdf_canvas) -> None:
        """
        Draw color palette legend on page 2.
        """
        from reportlab.lib.colors import HexColor
        
        legend_y = self.margin + 50
        legend_x = self.margin
        
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(legend_x, legend_y, "Color Palette:")
        
        pdf_canvas.setFont("Helvetica", 8)
        current_y = legend_y - 15
        colors_per_row = 3
        
        for i, color in enumerate(self.palette):
            if i % colors_per_row == 0 and i > 0:
                current_y -= 15
            
            current_x = legend_x + (i % colors_per_row) * 150
            
            # Draw color box
            box_size = 12
            try:
                # Use hex color for fill
                hex_color = f"#{color.hex_value}" if not color.hex_value.startswith("#") else color.hex_value
                pdf_canvas.setFillColor(HexColor(hex_color))
            except:
                # Fallback to RGB if hex conversion fails
                r, g, b = color.rgb
                pdf_canvas.setFillColor(r/255.0, g/255.0, b/255.0, alpha=1)
            
            pdf_canvas.rect(current_x, current_y - box_size, box_size, box_size, fill=1)
            
            # Draw border around color box
            pdf_canvas.setStrokeColor(HexColor("#000000"))
            pdf_canvas.setLineWidth(0.5)
            pdf_canvas.rect(current_x, current_y - box_size, box_size, box_size, stroke=1, fill=0)
            
            # Draw label
            pdf_canvas.setFillColor(HexColor("#000000"))  # Black text
            pdf_canvas.drawString(current_x + 15, current_y - box_size + 1, 
                                f"{color.label} - #{color.hex_value}")


def save_pdf(processed_image: Image.Image, palette: List[ColorPalette], output_path: str, merged_regions: bool = False, use_borders: bool = False) -> None:
    """
    Convenience function to generate and save a PDF (both pages in one file).
    
    Args:
        processed_image: Processed PIL Image
        palette: List of ColorPalette objects
        output_path: Path to save PDF
        merged_regions: If True, merge contiguous same-color regions
        use_borders: If True, draw colored borders instead of text labels
    """
    generator = PDFGenerator(processed_image, palette)
    generator.generate_pdf(output_path, merged_regions=merged_regions, use_borders=use_borders)


def save_pdf_separate(processed_image: Image.Image, palette: List[ColorPalette], output_path: str, merged_regions: bool = False, use_borders: bool = False) -> Tuple[str, str]:
    """
    Generate and save two separate PDFs: grid and final image.
    
    Args:
        processed_image: Processed PIL Image
        palette: List of ColorPalette objects
        output_path: Base path to save PDF files (without extension)
        merged_regions: If True, merge contiguous same-color regions
        use_borders: If True, draw colored borders instead of text labels
        
    Returns:
        Tuple of (grid_pdf_path, final_pdf_path)
    """
    # Remove .pdf extension if present
    if output_path.endswith('.pdf'):
        base_path = output_path[:-4]
    else:
        base_path = output_path
    
    grid_path = f"{base_path}_grid.pdf"
    final_path = f"{base_path}_final.pdf"
    
    # Create generator
    generator = PDFGenerator(processed_image, palette)
    
    # Save grid only
    grid_canvas = canvas.Canvas(grid_path, pagesize=A4)
    if merged_regions:
        if use_borders:
            generator._draw_grid_page_merged_borders(grid_canvas)
        else:
            generator._draw_grid_page_merged(grid_canvas)
    else:
        generator._draw_grid_page(grid_canvas)
    grid_canvas.save()
    
    # Save final image only
    final_canvas = canvas.Canvas(final_path, pagesize=A4)
    generator._draw_image_page(final_canvas)
    final_canvas.save()
    
    return grid_path, final_path
