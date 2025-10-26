// HairFastGAN-based Virtual Try-On
// This implementation uses a hairstyle transfer approach similar to HairFastGAN
// Reference: https://github.com/AIRI-Institute/HairFastGAN

class HairFastGANVirtualTryOn {
  constructor() {
    this.isInitialized = false;
    this.hairstyleLibrary = new Map();
    this.initializeHairstyleLibrary();
  }

  async initializeHairstyleLibrary() {
    // Map style names to reference images
    // In production, these would be actual hairstyle reference images
    const styleRefs = {
      'Modern Fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop',
      'Classic Fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop',
      'Textured Quiff': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=400&fit=crop',
      'Side Part': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=400&fit=crop',
      'Messy Crop': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=400&fit=crop',
      'Buzz Cut': 'https://images.unsplash.com/photo-1514790193030-c89d266d5a9d?w=400&h=400&fit=crop',
      'Undercut': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop'
    };

    for (const [style, refUrl] of Object.entries(styleRefs)) {
      this.hairstyleLibrary.set(style, refUrl);
    }

    this.isInitialized = true;
    console.log('✅ HairFastGAN virtual try-on initialized');
  }

  async processVirtualTryOn(userPhotoBase64, styleName) {
    try {
      console.log(`🎨 Processing virtual try-on for: ${styleName}`);
      
      // Get reference hairstyle image URL
      const referenceUrl = this.hairstyleLibrary.get(styleName);
      
      if (!referenceUrl) {
        throw new Error(`No reference image found for style: ${styleName}`);
      }

      // Call backend HairFastGAN endpoint
      const response = await fetch(`${API_URL}/virtual-tryon`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userPhoto: userPhotoBase64,
          hairstyleReference: referenceUrl,
          styleName: styleName
        })
      });

      if (!response.ok) {
        throw new Error('Failed to process virtual try-on');
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('❌ Virtual try-on processing error:', error);
      throw error;
    }
  }

  // Visualize the result (simple overlay approach until full model is integrated)
  visualizeResult(userPhotoElement, styleName, resultData) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      
      // Draw user photo
      ctx.drawImage(img, 0, 0);
      
      // In production with full HairFastGAN, this would show the transferred hairstyle
      // For now, add a visual indicator
      ctx.fillStyle = 'rgba(56, 189, 248, 0.3)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Add text indicating the style
      ctx.fillStyle = 'white';
      ctx.font = 'bold 24px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(styleName, canvas.width / 2, canvas.height / 2);
    };
    
    img.src = userPhotoElement.src;
    return canvas;
  }
}

// Export to global scope
window.HairFastGANVirtualTryOn = HairFastGANVirtualTryOn;

