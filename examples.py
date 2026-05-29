"""
Example: Using the Color-by-Numbers modules programmatically
This shows how to use the image processing and PDF generation without the GUI.
"""

from PIL import Image
from config import ColorPalette
from image_processor import ImageProcessor
from pdf_generator import save_pdf


def example_programmatic_usage():
    """
    Example 1: Process an image and generate PDF without GUI.
    """
    
    # Define color palette
    palette = [
        ColorPalette.from_hex("R", "#FF0000"),  # Red
        ColorPalette.from_hex("B", "#0000FF"),  # Blue
        ColorPalette.from_hex("Y", "#FFFF00"),  # Yellow
        ColorPalette.from_hex("K", "#000000"),  # Black
        ColorPalette.from_hex("W", "#FFFFFF"),  # White
    ]
    
    # Load and process image
    image = Image.open("your_image.jpg").convert('RGB')
    
    # Create processor
    processor = ImageProcessor(palette)
    
    # Process image to grid size (20x20)
    processed = processor.apply_standard_quantization(image, rows=20, columns=20)
    
    # Generate PDF
    save_pdf(processed, palette, "output.pdf")
    print("PDF saved as output.pdf")


def example_all_preview_options():
    """
    Example 2: Generate all three preview options.
    """
    
    palette = [
        ColorPalette.from_hex("R", "#FF0000"),
        ColorPalette.from_hex("G", "#00FF00"),
        ColorPalette.from_hex("B", "#0000FF"),
    ]
    
    image = Image.open("your_image.jpg").convert('RGB')
    processor = ImageProcessor(palette)
    
    # Generate all three options
    standard, enhanced, dithered = processor.generate_all_previews(image, 15, 15)
    
    # Save previews as images for comparison
    standard.save("preview_standard.png")
    enhanced.save("preview_enhanced.png")
    dithered.save("preview_dithered.png")
    print("Preview images saved")


def example_custom_processing():
    """
    Example 3: Custom image processing pipeline.
    """
    
    palette = [
        ColorPalette.from_hex("1", "#111111"),
        ColorPalette.from_hex("2", "#333333"),
        ColorPalette.from_hex("3", "#666666"),
        ColorPalette.from_hex("4", "#CCCCCC"),
        ColorPalette.from_hex("5", "#FFFFFF"),
    ]
    
    # Load image
    image = Image.open("your_image.jpg").convert('RGB')
    
    # Custom processing steps
    processor = ImageProcessor(palette)
    
    # Crop to specific region (example coordinates)
    cropped = processor.crop_to_viewport(image, (100, 100, 400, 400))
    
    # Resize to grid dimensions
    grid_image = processor.resize_to_grid(cropped, rows=30, columns=30)
    
    # Apply quantization
    quantized = processor.quantize_to_palette(grid_image)
    
    # Save and generate PDF
    quantized.save("processed_grid.png")
    save_pdf(quantized, palette, "custom_output.pdf")
    
    print("Custom processing complete")


def example_extract_from_image_region():
    """
    Example 4: Extract and process a specific region of an image.
    """
    
    palette = [
        ColorPalette.from_hex("A", "#E74C3C"),  # Red
        ColorPalette.from_hex("B", "#3498DB"),  # Blue
        ColorPalette.from_hex("C", "#2ECC71"),  # Green
        ColorPalette.from_hex("D", "#F39C12"),  # Orange
    ]
    
    image = Image.open("your_image.jpg").convert('RGB')
    processor = ImageProcessor(palette)
    
    # Define region of interest (left, top, right, bottom)
    region_bounds = (50, 50, 300, 300)
    
    # Crop to region
    region_image = processor.crop_to_viewport(image, region_bounds)
    
    # Process with dithering for best results
    processed = processor.apply_floyd_steinberg_dithering(region_image, 16, 16)
    
    # Generate PDF
    save_pdf(processed, palette, "region_output.pdf")
    print("Region extracted and saved")


if __name__ == "__main__":
    print("Color-by-Numbers: Programmatic Usage Examples")
    print("=" * 50)
    print()
    print("Uncomment the example you want to run and execute this file.")
    print()
    print("Available examples:")
    print("1. example_programmatic_usage() - Basic usage")
    print("2. example_all_preview_options() - Generate all three previews")
    print("3. example_custom_processing() - Custom processing pipeline")
    print("4. example_extract_from_image_region() - Extract specific regions")
    print()
    
    # Uncomment to run an example:
    # example_programmatic_usage()
