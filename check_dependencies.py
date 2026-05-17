"""
Dependency check and verification script.
Run this to ensure all required packages are installed before using the application.
"""

import sys


def check_dependencies():
    """Check if all required dependencies are installed."""
    
    print("Color-by-Numbers Converter - Dependency Check")
    print("=" * 50)
    print()
    
    dependencies = {
        "tkinter": "GUI Framework",
        "PIL (Pillow)": "Image Processing",
        "reportlab": "PDF Generation",
        "numpy": "Numerical Computing"
    }
    
    missing_packages = []
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    if sys.version_info < (3, 8):
        print("⚠️  WARNING: Python 3.8+ is recommended")
    print()
    
    # Check tkinter
    print("Checking dependencies...")
    print()
    try:
        import tkinter
        print("✓ tkinter (GUI Framework) - OK")
    except ImportError:
        print("✗ tkinter (GUI Framework) - MISSING")
        missing_packages.append("tkinter")
    
    # Check PIL/Pillow
    try:
        from PIL import Image
        import PIL
        print(f"✓ Pillow {PIL.__version__} (Image Processing) - OK")
    except ImportError:
        print("✗ Pillow (Image Processing) - MISSING")
        missing_packages.append("Pillow")
    
    # Check reportlab
    try:
        from reportlab import __version__ as rl_version
        print(f"✓ ReportLab {rl_version} (PDF Generation) - OK")
    except ImportError:
        print("✗ ReportLab (PDF Generation) - MISSING")
        missing_packages.append("reportlab")
    
    # Check numpy
    try:
        import numpy
        print(f"✓ NumPy {numpy.__version__} (Numerical Computing) - OK")
    except ImportError:
        print("✗ NumPy (Numerical Computing) - MISSING")
        missing_packages.append("numpy")
    
    print()
    print("=" * 50)
    
    if missing_packages:
        print(f"❌ Missing {len(missing_packages)} package(s):")
        print()
        print("Install using:")
        print("  pip install -r requirements.txt")
        print()
        print("Or manually:")
        for package in missing_packages:
            if package == "tkinter":
                print("  - tkinter: Usually included with Python")
                print("    Linux: sudo apt-get install python3-tk")
                print("    macOS: brew install python-tk")
            else:
                print(f"  pip install {package}")
        return False
    else:
        print("✅ All dependencies are installed!")
        print()
        print("You can now run the application with:")
        print("  python main.py")
        return True


def test_module_imports():
    """Test that our custom modules can be imported."""
    
    print()
    print("Testing custom modules...")
    print()
    
    try:
        import config
        print("✓ config module - OK")
    except Exception as e:
        print(f"✗ config module - ERROR: {e}")
        return False
    
    try:
        import image_processor
        print("✓ image_processor module - OK")
    except Exception as e:
        print(f"✗ image_processor module - ERROR: {e}")
        return False
    
    try:
        import pdf_generator
        print("✓ pdf_generator module - OK")
    except Exception as e:
        print(f"✗ pdf_generator module - ERROR: {e}")
        return False
    
    try:
        import main
        print("✓ main module - OK")
    except Exception as e:
        print(f"✗ main module - ERROR: {e}")
        return False
    
    print()
    print("✅ All modules loaded successfully!")
    return True


def main():
    """Run all checks."""
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if deps_ok:
        # Test module imports
        modules_ok = test_module_imports()
        
        if modules_ok:
            print()
            print("=" * 50)
            print("🎉 Ready to use! Run: python main.py")
            print("=" * 50)
            return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
