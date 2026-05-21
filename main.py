"""
Main application GUI for the Color-by-Numbers converter.
Uses Tkinter for the interface and manages all phases of conversion.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import os
from typing import List, Optional, Tuple
from config import ColorPalette, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, CANVAS_WIDTH, CANVAS_HEIGHT, DEFAULT_ROWS, DEFAULT_COLUMNS
from image_processor import ImageProcessor
from pdf_generator import save_pdf, save_pdf_separate


class ColorByNumbersApp:
    """Main application class."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Color-by-Numbers Converter")
        # Open window in fullscreen by default
        self.root.state('zoomed')  # Maximize window (Windows)
        
        # State variables
        self.current_phase = 1  # 1=Config, 2=Cropping, 3=Preview+PDF
        self.original_image: Optional[Image.Image] = None
        self.cropped_image: Optional[Image.Image] = None
        self.current_full_image: Optional[Image.Image] = None  # For zoom popup
        self.processed_previews: dict = {}  # Store all algorithm previews
        self.selected_preview: Optional[str] = None  # Which algorithm was selected
        
        self.rows = DEFAULT_ROWS
        self.columns = DEFAULT_COLUMNS
        self.palette: List[ColorPalette] = self._create_default_palette()
        self.image_processor: Optional[ImageProcessor] = None
        
        # Canvas state for pan/zoom
        self.canvas_image_id = None
        self.pan_start = None
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.image_scale = 1.0
        self.canvas_image_tk: Optional[ImageTk.PhotoImage] = None
        
        self._show_phase_1()
    
    def _create_default_palette(self) -> List[ColorPalette]:
        """Create a default color palette."""
        return [
            ColorPalette.from_hex("R", "#FF0000"),  # Red
            ColorPalette.from_hex("G", "#00FF00"),  # Green
            ColorPalette.from_hex("B", "#0000FF"),  # Blue
            ColorPalette.from_hex("Y", "#FFFF00"),  # Yellow
            ColorPalette.from_hex("O", "#FFA500"),  # Orange
            ColorPalette.from_hex("K", "#000000"),  # Black
            ColorPalette.from_hex("W", "#FFFFFF"),  # White
        ]
    
    def _clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    # ============================================================
    # PHASE 1: Configuration & Upload
    # ============================================================
    
    def _show_phase_1(self):
        """Display Phase 1: Configuration and Upload."""
        self._clear_window()
        self.current_phase = 1
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Phase 1: Configuration & Upload", 
                         font=("Helvetica", 16, "bold"))
        title.pack(pady=10)
        
        # Grid configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Grid Configuration", padding="10")
        config_frame.pack(fill=tk.X, pady=10)
        
        # Rows input
        ttk.Label(config_frame, text="Rows:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.rows_entry = ttk.Entry(config_frame, width=10)
        self.rows_entry.insert(0, str(self.rows))
        self.rows_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Columns input
        ttk.Label(config_frame, text="Columns:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.columns_entry = ttk.Entry(config_frame, width=10)
        self.columns_entry.insert(0, str(self.columns))
        self.columns_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Color palette frame
        palette_frame = ttk.LabelFrame(main_frame, text="Color Palette", padding="10")
        palette_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Palette entries (scrollable)
        canvas = tk.Canvas(palette_frame)
        scrollbar = ttk.Scrollbar(palette_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.palette_entries = []
        self.color_preview_labels = []  # Store preview labels for live updates
        for i, color in enumerate(self.palette):
            color_frame = ttk.Frame(scrollable_frame)
            color_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(color_frame, text=f"Color {i+1}:").pack(side=tk.LEFT, padx=5)
            
            # Label entry
            label_entry = ttk.Entry(color_frame, width=3)
            label_entry.insert(0, color.label)
            label_entry.pack(side=tk.LEFT, padx=5)
            
            # Hex entry
            hex_entry = ttk.Entry(color_frame, width=12)
            hex_entry.insert(0, f"#{color.hex_value}")
            hex_entry.pack(side=tk.LEFT, padx=5)
            
            self.palette_entries.append((label_entry, hex_entry, color_frame))
            
            # Color preview - bind to update on change
            preview_color = f"#{color.hex_value}"
            try:
                preview = tk.Label(color_frame, bg=preview_color, width=3, height=1, relief=tk.SUNKEN, bd=1)
                preview.pack(side=tk.LEFT, padx=5)
                
                # Bind hex entry to update preview in real-time
                hex_entry.bind("<KeyRelease>", lambda e, prev=preview, entry=hex_entry: self._update_color_preview(prev, entry))
                self.color_preview_labels.append((preview, hex_entry))
            except Exception as e:
                print(f"Error creating color preview: {e}")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add color button
        add_color_btn = ttk.Button(main_frame, text="Add Color", command=self._add_palette_color)
        add_color_btn.pack(pady=5)
        
        # Upload button
        upload_frame = ttk.Frame(main_frame)
        upload_frame.pack(fill=tk.X, pady=20)
        
        upload_btn = ttk.Button(upload_frame, text="Upload Image", command=self._upload_image)
        upload_btn.pack(side=tk.LEFT, padx=5)
    
    def _add_palette_color(self):
        """Add a new color to the palette."""
        new_color = ColorPalette.from_hex("X", "#CCCCCC")
        self.palette.append(new_color)
        self._show_phase_1()  # Refresh the display
    
    def _update_color_preview(self, preview_label, hex_entry):
        """Update color preview when hex value changes."""
        try:
            hex_value = hex_entry.get().strip()
            if not hex_value.startswith('#'):
                hex_value = '#' + hex_value
            # Try to set the background color
            preview_label.config(bg=hex_value)
        except tk.TclError:
            # Invalid color format - preview stays as is
            pass
    
    def _validate_hex_color(self, hex_value: str) -> Tuple[bool, str]:
        """Validate a hex color value and return (is_valid, formatted_hex_value)."""
        hex_value = hex_value.strip()
        if not hex_value:
            return False, "Color value is empty"
        
        # Remove # if present
        if hex_value.startswith('#'):
            hex_value = hex_value[1:]
        
        # Check length
        if len(hex_value) != 6:
            return False, f"Hex values must be 6 characters (e.g., #FF0000), got: {hex_value}"
        
        # Check if all characters are valid hex
        try:
            int(hex_value, 16)
            return True, f"#{hex_value.upper()}"
        except ValueError:
            return False, f"Invalid hex characters in: {hex_value}"
    
    def _upload_image(self):
        """Handle image upload."""
        try:
            # Validate inputs
            self.rows = int(self.rows_entry.get())
            self.columns = int(self.columns_entry.get())
            
            if self.rows <= 0 or self.columns <= 0:
                messagebox.showerror("Invalid Input", "Rows and columns must be positive integers.")
                return
            
            # Update palette from entries
            self.palette = []
            for label_entry, hex_entry, _ in self.palette_entries:
                label = label_entry.get().strip()
                hex_value = hex_entry.get().strip()
                
                if not label or not hex_value:
                    continue
                
                # Validate label
                if len(label) > 1:
                    messagebox.showerror(
                        "Invalid Label", 
                        f"Color label must be a single character, got: '{label}'"
                    )
                    return
                
                # Validate hex color
                is_valid, result = self._validate_hex_color(hex_value)
                if not is_valid:
                    messagebox.showerror(
                        "Invalid Color Format", 
                        f"Color '{label}': {result}\n\nExample: #FF0000 for Red"
                    )
                    return
                
                try:
                    color = ColorPalette.from_hex(label, result)
                    self.palette.append(color)
                except Exception as e:
                    messagebox.showerror(
                        "Color Error", 
                        f"Error creating color '{label}' with {result}:\n{str(e)}"
                    )
                    return
            
            if len(self.palette) < 2:
                messagebox.showerror("Invalid Palette", "Please define at least 2 colors.")
                return
            
            # Open file dialog
            file_path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
            
            # Load image
            self.original_image = Image.open(file_path).convert('RGB')
            self.image_processor = ImageProcessor(self.palette)
            
            # Move to Phase 2
            self._show_phase_2()
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Rows and columns must be integers.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    # ============================================================
    # PHASE 2: Viewport Cropping (Pan & Zoom)
    # ============================================================
    
    def _show_phase_2(self):
        """Display Phase 2: Viewport Cropping with Pan and Zoom."""
        self._clear_window()
        self.current_phase = 2
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame (PACK FIRST - at bottom to ensure visibility)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        reset_btn = ttk.Button(control_frame, text="Reset View", command=self._reset_view)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        back_btn = ttk.Button(control_frame, text="< Back", command=self._show_phase_1)
        back_btn.pack(side=tk.LEFT, padx=5)
        
        # Make the Confirm button stand out more
        confirm_btn = ttk.Button(control_frame, text="✓ Confirm Crop >", command=self._confirm_crop)
        confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        
        title = ttk.Label(title_frame, text="Phase 2: Viewport Cropping (Pan & Zoom)", 
                         font=("Helvetica", 16, "bold"))
        title.pack(side=tk.LEFT)
        
        # Instructions
        instructions = ttk.Label(title_frame, text="Click and drag to pan • Scroll to zoom", 
                                font=("Helvetica", 10, "italic"), foreground="gray")
        instructions.pack(side=tk.LEFT, padx=20)
        
        # Canvas for image display and interaction
        # Create a fixed-size canvas container to avoid button being pushed off-screen
        canvas_container = ttk.Frame(main_frame)
        canvas_container.pack(pady=10, fill=tk.BOTH, expand=False)
        
        self.crop_canvas = tk.Canvas(canvas_container, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, 
                                     bg="gray20", cursor="hand2")
        self.crop_canvas.pack()
        
        # Add grid info display
        grid_info_frame = ttk.Frame(main_frame)
        grid_info_frame.pack(fill=tk.X, pady=5)
        aspect_ratio = self.columns / self.rows
        ttk.Label(grid_info_frame, text=f"Grid: {self.rows}×{self.columns} | Aspect Ratio: {aspect_ratio:.2f} (Width:Height)", 
                 font=("Helvetica", 9), foreground="gray").pack()
        
        # Bind events for pan and zoom
        self.crop_canvas.bind("<B1-Motion>", self._canvas_pan)
        self.crop_canvas.bind("<Button-1>", self._canvas_pan_start)
        self.crop_canvas.bind("<MouseWheel>", self._canvas_zoom)
        self.crop_canvas.bind("<Button-4>", self._canvas_zoom)  # Linux scroll up
        self.crop_canvas.bind("<Button-5>", self._canvas_zoom)  # Linux scroll down
        
        # Calculate viewport
        aspect_ratio = self.columns / self.rows
        self._calculate_viewport()
        
        # Draw initial image
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.image_scale = 1.0
        self._draw_canvas_image()
    
    def _calculate_viewport(self):
        """Calculate the viewport dimensions based on grid aspect ratio."""
        aspect_ratio = self.columns / self.rows
        canvas_aspect = CANVAS_WIDTH / CANVAS_HEIGHT
        
        if aspect_ratio > canvas_aspect:
            # Wider than canvas - limit by width
            self.viewport_width = CANVAS_WIDTH * 0.8
            self.viewport_height = self.viewport_width / aspect_ratio
        else:
            # Taller than canvas - limit by height
            self.viewport_height = CANVAS_HEIGHT * 0.8
            self.viewport_width = self.viewport_height * aspect_ratio
        
        self.viewport_x = (CANVAS_WIDTH - self.viewport_width) / 2
        self.viewport_y = (CANVAS_HEIGHT - self.viewport_height) / 2
    
    def _draw_canvas_image(self):
        """Draw the image and viewport frame on the canvas."""
        self.crop_canvas.delete("all")
        
        # Draw darkened background outside viewport
        self.crop_canvas.create_rectangle(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, 
                                        fill="gray10", outline="")
        
        # Draw image
        if self.original_image:
            # Calculate scaled image dimensions
            scaled_width = int(self.original_image.width * self.image_scale)
            scaled_height = int(self.original_image.height * self.image_scale)
            
            # Resize image
            display_image = self.original_image.resize((scaled_width, scaled_height), Image.Resampling.BILINEAR)
            
            # Convert to PhotoImage
            self.canvas_image_tk = ImageTk.PhotoImage(display_image)
            
            # Draw image at offset
            self.crop_canvas.create_image(
                int(CANVAS_WIDTH / 2 + self.image_offset_x),
                int(CANVAS_HEIGHT / 2 + self.image_offset_y),
                image=self.canvas_image_tk
            )
        
        # Draw viewport frame (bright border)
        self.crop_canvas.create_rectangle(
            self.viewport_x, self.viewport_y,
            self.viewport_x + self.viewport_width, self.viewport_y + self.viewport_height,
            outline="cyan", width=3
        )
        
        # Add dimension text to viewport
        viewport_center_x = self.viewport_x + self.viewport_width / 2
        viewport_center_y = self.viewport_y + self.viewport_height / 2
        dim_text = f"{self.columns}×{self.rows} grid\n({self.viewport_width:.0f}×{self.viewport_height:.0f}px)"
        self.crop_canvas.create_text(
            viewport_center_x, viewport_center_y,
            text=dim_text,
            font=("Helvetica", 11, "bold"),
            fill="cyan"
        )
        
        # Draw semi-transparent overlay outside viewport
        self.crop_canvas.create_rectangle(
            0, 0, CANVAS_WIDTH, CANVAS_HEIGHT,
            outline="", fill="", stipple="gray50"
        )
    
    def _canvas_pan_start(self, event):
        """Start panning operation."""
        self.pan_start = (event.x, event.y)
    
    def _canvas_pan(self, event):
        """Handle image panning."""
        if self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            
            self.image_offset_x += dx
            self.image_offset_y += dy
            self.pan_start = (event.x, event.y)
            
            self._draw_canvas_image()
    
    def _canvas_zoom(self, event):
        """Handle image zooming."""
        # Determine zoom direction
        if event.num == 5 or event.delta < 0:
            scale_factor = 0.9  # Zoom out
        else:
            scale_factor = 1.1  # Zoom in
        
        self.image_scale *= scale_factor
        self.image_scale = max(0.2, min(5.0, self.image_scale))  # Clamp zoom level
        
        self._draw_canvas_image()
    
    def _reset_view(self):
        """Reset the image view to default."""
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.image_scale = 1.0
        self._draw_canvas_image()
    
    def _confirm_crop(self):
        """Confirm the crop and extract viewport area."""
        if not self.original_image:
            messagebox.showerror("Error", "No image loaded.")
            return
        
        try:
            # Calculate the bounding box of the original image that's visible in the viewport
            # This requires transforming viewport coordinates back to image coordinates
            
            # Viewport position in canvas space
            vp_x1 = self.viewport_x
            vp_y1 = self.viewport_y
            vp_x2 = self.viewport_x + self.viewport_width
            vp_y2 = self.viewport_y + self.viewport_height
            
            # Image center in canvas space
            img_center_x = CANVAS_WIDTH / 2 + self.image_offset_x
            img_center_y = CANVAS_HEIGHT / 2 + self.image_offset_y
            
            # Scaled image dimensions
            scaled_width = self.original_image.width * self.image_scale
            scaled_height = self.original_image.height * self.image_scale
            
            # Image corners in canvas space
            img_x1 = img_center_x - scaled_width / 2
            img_y1 = img_center_y - scaled_height / 2
            img_x2 = img_center_x + scaled_width / 2
            img_y2 = img_center_y + scaled_height / 2
            
            # Find intersection of viewport and image
            intersect_x1 = max(vp_x1, img_x1)
            intersect_y1 = max(vp_y1, img_y1)
            intersect_x2 = min(vp_x2, img_x2)
            intersect_y2 = min(vp_y2, img_y2)
            
            # Transform back to original image coordinates
            if scaled_width > 0 and scaled_height > 0:
                crop_x1 = (intersect_x1 - img_x1) / self.image_scale
                crop_y1 = (intersect_y1 - img_y1) / self.image_scale
                crop_x2 = (intersect_x2 - img_x1) / self.image_scale
                crop_y2 = (intersect_y2 - img_y1) / self.image_scale
                
                # Clamp to image bounds
                crop_x1 = max(0, min(self.original_image.width, crop_x1))
                crop_y1 = max(0, min(self.original_image.height, crop_y1))
                crop_x2 = max(0, min(self.original_image.width, crop_x2))
                crop_y2 = max(0, min(self.original_image.height, crop_y2))
                
                # Crop the image
                self.cropped_image = self.image_processor.crop_to_viewport(
                    self.original_image,
                    (crop_x1, crop_y1, crop_x2, crop_y2)
                )
                
                if self.cropped_image.width > 0 and self.cropped_image.height > 0:
                    self._show_phase_3()
                else:
                    messagebox.showerror("Invalid Crop", "The cropped area is too small.")
            
        except Exception as e:
            messagebox.showerror("Crop Error", f"Failed to crop image: {str(e)}")
    
    # ============================================================
    # PHASE 3: Preview Generation
    # ============================================================
    
    def _show_phase_3(self):
        """Display Phase 3: Master-Detail Algorithm Selection and Preview."""
        self._clear_window()
        self.current_phase = 3
        
        # Create selected method variable
        self.selected_method_var = tk.StringVar()
        
        # Create main PanedWindow for 30/70 split
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, bg="gray40")
        main_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # ============================================================
        # LEFT PANE (30%): Method Selector with Dynamic Aspect Ratio Thumbnails
        # ============================================================
        left_pane = ttk.Frame(main_paned, padding="0")
        main_paned.add(left_pane, width=int(self.root.winfo_width() * 0.3))
        
        # Title
        title = ttk.Label(left_pane, text="Select Algorithm", font=("Helvetica", 13, "bold"))
        title.pack(pady=12, padx=10)
        
        # Scrollable frame for method cards
        scroll_canvas = tk.Canvas(left_pane, bg="gray85", highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_pane, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scrollable_frame = ttk.Frame(scroll_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        
        scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Clear old previews from previous image to prevent caching issues
        self.processed_previews = {}
        
        # Store references
        self.method_cards = {}
        self.method_thumbnails = {}
        self.method_radios = {}
        self.method_images = {}
        
        # Get all 10 algorithms
        algorithms = self.image_processor.get_all_algorithms()
        
        # Calculate thumbnail dimensions based on grid aspect ratio
        aspect_ratio = self.columns / self.rows  # width / height
        thumb_width = 260  # Fill left panel width (30% - padding)
        thumb_height = int(thumb_width / aspect_ratio)
        
        # Generate and cache processed images for thumbnails
        processed_images = {}
        for algo_key, (algo_name, algo_method) in algorithms.items():
            try:
                # Process with algorithm
                processed_image = algo_method(self.cropped_image, self.rows, self.columns)
                processed_images[algo_key] = processed_image
                print(f"✓ {algo_name} generated successfully")
            except Exception as e:
                print(f"✗ {algo_name} failed: {str(e)}")
                processed_images[algo_key] = None
        
        # Create method cards with clickable thumbnails
        for algo_key, (algo_name, algo_method) in algorithms.items():
            # Card frame
            card_frame = tk.Frame(scrollable_frame, bg="white", relief=tk.RAISED, bd=2)
            card_frame.pack(fill=tk.X, pady=8, padx=6)
            
            # Header with algorithm name and radio button
            header_frame = tk.Frame(card_frame, bg="white")
            header_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
            
            radio_btn = tk.Radiobutton(
                header_frame,
                text=algo_name,
                variable=self.selected_method_var,
                value=algo_key,
                command=lambda k=algo_key: self._render_main_preview(k, None),
                font=("Helvetica", 10, "bold"),
                bg="white",
                selectcolor="white"
            )
            radio_btn.pack(anchor="w")
            self.method_radios[algo_key] = radio_btn
            
            # Thumbnail image (aspect ratio aware, clickable)
            thumb_label = tk.Label(card_frame, bg="gray60", cursor="hand2")
            
            # Create thumbnail with correct aspect ratio
            if processed_images[algo_key]:
                # Scale thumbnail to fill panel width while maintaining aspect ratio
                thumb_image = processed_images[algo_key].copy()
                thumb_image = thumb_image.resize((thumb_width, thumb_height), Image.Resampling.NEAREST)
                
                # Store original processed image for main canvas
                self.method_images[algo_key] = processed_images[algo_key]
                
                # Convert to PhotoImage for display
                photo_image = ImageTk.PhotoImage(thumb_image)
                thumb_label.config(image=photo_image, width=thumb_width, height=thumb_height)
                thumb_label.image = photo_image  # Keep reference
                
                # Make thumbnail clickable
                thumb_label.bind(
                    "<Button-1>",
                    lambda e, k=algo_key: (self.selected_method_var.set(k), self._render_main_preview(k, None))
                )
            
            thumb_label.pack(padx=8, pady=8, fill=tk.BOTH)
            
            # Make card frame clickable too
            card_frame.bind(
                "<Button-1>",
                lambda e, k=algo_key: (self.selected_method_var.set(k), self._render_main_preview(k, None))
            )
            
            self.method_cards[algo_key] = card_frame
        
        # ============================================================
        # RIGHT PANE (70%): Main Preview Canvas (Massive Dynamic)
        # ============================================================
        right_pane = ttk.Frame(main_paned)
        main_paned.add(right_pane, width=int(self.root.winfo_width() * 0.7))
        
        # Title
        title_right = ttk.Label(right_pane, text="Preview", font=("Helvetica", 13, "bold"))
        title_right.pack(pady=12, padx=10)
        
        # Main preview canvas (fill available space)
        self.main_canvas = tk.Canvas(right_pane, bg="#1a1a1a", highlightthickness=2, highlightbackground="gray60")
        self.main_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Bind canvas resize event
        self.main_canvas.bind("<Configure>", self._on_canvas_resize)
        
        # Bottom control frame
        control_frame = ttk.Frame(right_pane)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        generate_pdf_btn = ttk.Button(
            control_frame,
            text="✓ Generate A4 PDF",
            command=self._download_pdf
        )
        generate_pdf_btn.pack(side=tk.LEFT, padx=5)
        
        back_btn = ttk.Button(
            control_frame,
            text="< Back to Crop",
            command=self._show_phase_2
        )
        back_btn.pack(side=tk.RIGHT, padx=5)
        
        # Select first algorithm by default
        first_algo = list(algorithms.items())[0]
        self.selected_method_var.set(first_algo[0])
        self._render_main_preview(first_algo[0], None)
    
    def _on_canvas_resize(self, event):
        """Handle canvas resize to rescale the preview image."""
        if hasattr(self, 'current_full_image') and self.current_full_image is not None:
            self._render_main_preview(self.selected_preview, None, is_resize=True)
    
    def _render_main_preview(self, algo_key: str, algo_method, is_resize=False):
        """Render the selected algorithm in the main preview canvas."""
        try:
            # Use cached processed image or generate if needed
            if algo_key in self.method_images:
                processed_image = self.method_images[algo_key]
            elif not is_resize or algo_key not in self.processed_previews:
                # Get method from algorithms if not provided
                if algo_method is None:
                    algorithms = self.image_processor.get_all_algorithms()
                    algo_method = algorithms[algo_key][1]
                
                processed_image = algo_method(self.cropped_image, self.rows, self.columns)
                self.processed_previews[algo_key] = processed_image
            else:
                processed_image = self.processed_previews[algo_key]
            
            # Always cache to processed_previews for PDF generation
            if algo_key not in self.processed_previews:
                self.processed_previews[algo_key] = processed_image
            
            # Store for PDF generation
            self.selected_preview = algo_key
            self.current_full_image = processed_image
            
            # Get canvas dimensions
            canvas_width = self.main_canvas.winfo_width()
            canvas_height = self.main_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                self.main_canvas.after(10, lambda: self._render_main_preview(algo_key, algo_method, is_resize))
                return
            
            # Calculate scaling to maximize size without distortion
            img_width, img_height = processed_image.size
            aspect_ratio = img_width / img_height
            canvas_aspect = canvas_width / canvas_height
            
            if aspect_ratio > canvas_aspect:
                # Image wider than canvas - scale to canvas width
                new_width = int(canvas_width * 0.95)
                new_height = int(new_width / aspect_ratio)
            else:
                # Image taller than canvas - scale to canvas height
                new_height = int(canvas_height * 0.95)
                new_width = int(new_height * aspect_ratio)
            
            # Resize using NEAREST for sharp pixels
            display_image = processed_image.resize((new_width, new_height), Image.Resampling.NEAREST)
            
            # Convert to PhotoImage
            photo_image = ImageTk.PhotoImage(display_image)
            
            # Clear canvas and display image centered
            self.main_canvas.delete("all")
            
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            
            self.main_canvas.create_image(x, y, image=photo_image, anchor=tk.NW)
            self.main_canvas_photo = photo_image  # Keep reference
            
        except Exception as e:
            messagebox.showerror("Algorithm Error", f"Failed to process image: {str(e)}")
    
    # ============================================================
    # PHASE 4: PDF Generation
    # ============================================================
    

    
    def _download_pdf(self):
        """Generate and save the PDF."""
        try:
            # Ask user which format they want
            format_choice = messagebox.askyesnocancel(
                "PDF Format",
                "How would you like to save the PDF?\n\n"
                "YES: Two separate files (grid + final image)\n"
                "NO: Single file with both pages\n"
                "CANCEL: Don't save"
            )
            
            if format_choice is None:
                print("User cancelled save dialog")
                return
            
            # Ask about grid style (traditional or merged regions)
            style_choice = messagebox.askyesnocancel(
                "Grid Style",
                "How should the grid be labeled?\n\n"
                "YES: Merged Regions (erase shared borders, label sections)\n"
                "NO: Traditional (each pixel labeled separately)\n"
                "CANCEL: Don't save"
            )
            
            if style_choice is None:
                print("User cancelled save dialog")
                return
            
            # If merged regions, ask about label type
            use_borders = False
            if style_choice:  # Merged regions mode
                label_choice = messagebox.askyesnocancel(
                    "Label Style",
                    "How should regions be marked?\n\n"
                    "YES: Colored Borders (thin colored lines showing region color)\n"
                    "NO: Text Labels (number/letter labels in each region)\n"
                    "CANCEL: Don't save"
                )
                
                if label_choice is None:
                    print("User cancelled save dialog")
                    return
                
                use_borders = label_choice  # True = borders, False = text labels
            
            # Open save dialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            if not file_path:
                print("User cancelled save dialog")
                return
            
            print(f"Attempting to save PDF to: {file_path}")
            print(f"Selected preview: {self.selected_preview}")
            print(f"Available previews: {list(self.processed_previews.keys())}")
            print(f"Grid style: {'Merged Regions' if style_choice else 'Traditional'}")
            print(f"Label style: {'Colored Borders' if use_borders else 'Text Labels'}")
            
            # Generate PDF
            if self.selected_preview and self.selected_preview in self.processed_previews:
                processed_image = self.processed_previews[self.selected_preview]
                print(f"Processing image: {processed_image.size}")
                
                if format_choice:  # YES - separate files
                    grid_path, final_path = save_pdf_separate(processed_image, self.palette, file_path, merged_regions=style_choice, use_borders=use_borders)
                    print(f"Grid PDF saved to: {grid_path}")
                    print(f"Final PDF saved to: {final_path}")
                    messagebox.showinfo("Success", f"PDFs saved successfully:\n\n{grid_path}\n{final_path}")
                else:  # NO - single file
                    save_pdf(processed_image, self.palette, file_path, merged_regions=style_choice, use_borders=use_borders)
                    print(f"PDF saved to: {file_path}")
                    messagebox.showinfo("Success", f"PDF saved successfully:\n{file_path}")
                
                # Option to start over
                if messagebox.askyesno("New Conversion", "Would you like to convert another image?"):
                    self.current_phase = 0
                    self._show_phase_1()
            else:
                print(f"ERROR: selected_preview={self.selected_preview}, in processed_previews={self.selected_preview in self.processed_previews}")
                messagebox.showerror("Error", "No image selected or processed. Please select an algorithm first.")
                
        except Exception as e:
            print(f"Exception in _download_pdf: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Save Error", f"Failed to save PDF: {str(e)}")


def main():
    """Entry point for the application."""
    root = tk.Tk()
    app = ColorByNumbersApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
