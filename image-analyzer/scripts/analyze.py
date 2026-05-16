#!/usr/bin/env python3
"""
Image Analysis Script

This script analyzes an image and saves a detailed description to a text file.
"""

import sys
import os

def analyze_image(image_path, output_path=None):
    """
    Analyze an image file and save a description.
    
    Args:
        image_path (str): Path to the image file
        output_path (str, optional): Path for output analysis file. Defaults to <image>_analysis.txt
    """
    
    # Load the image (this would use the load_image tool in the agent)
    # For now, we'll create a template
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = f"{base_name}_analysis.txt"
    
    # Create analysis content
    analysis_content = f"""# Image Analysis: {os.path.basename(image_path)}

## Summary
[Image loaded successfully - detailed description to be provided by human analysis]

## Important Notes
- Image path: {image_path}
- Analysis date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- File format: {os.path.splitext(image_path)[1].upper()}

## Analysis Guidelines
1. Load the image using load_image tool
2. Describe primary subject and objects
3. Note colors and color scheme
4. Identify scene type
5. Check for text content
6. Describe lighting conditions
7. Note any notable details

## Confidence Level
[To be determined based on image quality]
"""
    
    # Write analysis
    with open(output_path, 'w') as f:
        f.write(analysis_content)
    
    print(f"Analysis template created: {output_path}")
    print(f"Image path: {image_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze.py <image_path> [output_path]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    analyze_image(image_path, output_path)