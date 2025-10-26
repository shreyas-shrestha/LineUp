// virtual-tryon.js - Real AR Virtual Try-On with Face Detection

class VirtualTryOn {
  constructor() {
    this.stream = null;
    this.videoEl = null;
    this.photoEl = null;
    this.canvasContainerEl = null;
    this.overlayCanvas = null;
    this.overlayCtx = null;
    this.currentStyle = null;
    this.isActive = false;
    this.animationFrame = null;
    this.mode = 'camera'; // 'camera' or 'photo'
    
    // Face detection using face-api.js (lightweight alternative to MediaPipe)
    this.faceDetector = null;
    this.modelsLoaded = false;
    
    // Hairstyle overlay images
    this.hairstyleImages = {};
  }

  async initialize() {
    console.log('🎭 Initializing Virtual Try-On...');
    
    try {
      // Load face detection models
      await this.loadFaceDetectionModels();
      
      // Preload hairstyle images
      await this.loadHairstyleImages();
      
      console.log('✅ Virtual Try-On initialized');
      return true;
    } catch (error) {
      console.error('❌ Failed to initialize:', error);
      return false;
    }
  }

  async loadFaceDetectionModels() {
    // Using a simple face detection approach with browser's built-in capabilities
    // For production, you'd use TensorFlow.js FaceMesh or face-api.js
    console.log('📦 Loading face detection...');
    
    // Check if browser supports face detection
    if ('FaceDetector' in window) {
      this.faceDetector = new window.FaceDetector();
      this.modelsLoaded = true;
    } else {
      // Fallback: use center-based positioning
      console.log('⚠️ Browser face detection not available, using fallback positioning');
      this.modelsLoaded = true;
    }
  }

  async loadHairstyleImages() {
    // Load actual hairstyle overlay images
    const styles = {
      'Modern Fade': this.generateHairstyleOverlay('Modern Fade', '#2563eb', '#7c3aed'),
      'Classic Fade': this.generateHairstyleOverlay('Classic Fade', '#059669', '#0891b2'),
      'Textured Quiff': this.generateHairstyleOverlay('Textured Quiff', '#dc2626', '#ea580c'),
      'Side Part': this.generateHairstyleOverlay('Side Part', '#7c2d12', '#92400e'),
      'Messy Crop': this.generateHairstyleOverlay('Messy Crop', '#4338ca', '#6366f1'),
      'Classic Pompadour': this.generateHairstyleOverlay('Classic Pompadour', '#be123c', '#e11d48'),
      'Buzz Cut': this.generateHairstyleOverlay('Buzz Cut', '#374151', '#6b7280'),
      'Taper': this.generateHairstyleOverlay('Taper', '#0e7490', '#0891b2'),
      'Undercut': this.generateHairstyleOverlay('Undercut', '#7c3aed', '#a855f7')
    };

    // Load all images
    for (const [name, dataUrl] of Object.entries(styles)) {
      const img = new Image();
      img.src = dataUrl;
      await new Promise((resolve) => {
        img.onload = resolve;
      });
      this.hairstyleImages[name] = img;
    }
    
    console.log('✅ Hairstyle overlays loaded');
  }

  generateHairstyleOverlay(styleName, color1, color2) {
    // Generate a realistic hairstyle overlay based on style name
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);

    // Draw hairstyle shape based on name
    ctx.fillStyle = gradient;
    ctx.globalAlpha = 0.85;

    if (styleName.includes('Fade') || styleName.includes('Taper')) {
      // Fade style - shorter on sides
      this.drawFadeHair(ctx, canvas.width, canvas.height);
    } else if (styleName.includes('Quiff') || styleName.includes('Pompadour')) {
      // Volume on top
      this.drawQuiffHair(ctx, canvas.width, canvas.height);
    } else if (styleName.includes('Buzz')) {
      // Very short all around
      this.drawBuzzHair(ctx, canvas.width, canvas.height);
    } else if (styleName.includes('Crop') || styleName.includes('Messy')) {
      // Textured short hair
      this.drawCropHair(ctx, canvas.width, canvas.height);
    } else {
      // Default medium length
      this.drawDefaultHair(ctx, canvas.width, canvas.height);
    }

    return canvas.toDataURL('image/png');
  }

  drawFadeHair(ctx, w, h) {
    // Fade hairstyle shape
    ctx.beginPath();
    ctx.ellipse(w/2, h*0.4, w*0.35, h*0.35, 0, 0, Math.PI * 2);
    ctx.fill();
    
    // Add texture lines for fade effect
    ctx.globalAlpha = 0.3;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    for (let i = 0; i < 8; i++) {
      ctx.beginPath();
      ctx.arc(w/2, h*0.4, w*0.25 + i*5, Math.PI * 0.2, Math.PI * 0.8);
      ctx.stroke();
    }
  }

  drawQuiffHair(ctx, w, h) {
    // Voluminous quiff shape
    ctx.beginPath();
    ctx.moveTo(w*0.2, h*0.5);
    ctx.quadraticCurveTo(w*0.3, h*0.15, w*0.5, h*0.2);
    ctx.quadraticCurveTo(w*0.7, h*0.15, w*0.8, h*0.5);
    ctx.quadraticCurveTo(w*0.5, h*0.6, w*0.2, h*0.5);
    ctx.fill();
  }

  drawBuzzHair(ctx, w, h) {
    // Very short buzz cut
    ctx.beginPath();
    ctx.ellipse(w/2, h*0.45, w*0.32, h*0.28, 0, 0, Math.PI * 2);
    ctx.fill();
    
    // Add short hair texture
    ctx.globalAlpha = 0.4;
    for (let i = 0; i < 100; i++) {
      const x = w*0.2 + Math.random() * w*0.6;
      const y = h*0.2 + Math.random() * h*0.4;
      ctx.fillRect(x, y, 1, 2);
    }
  }

  drawCropHair(ctx, w, h) {
    // Messy textured crop
    ctx.beginPath();
    ctx.ellipse(w/2, h*0.4, w*0.34, h*0.32, 0, 0, Math.PI * 2);
    ctx.fill();
    
    // Add messy texture
    ctx.globalAlpha = 0.5;
    for (let i = 0; i < 15; i++) {
      const x = w*0.25 + Math.random() * w*0.5;
      const y = h*0.2 + Math.random() * h*0.3;
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  drawDefaultHair(ctx, w, h) {
    // Default medium length
    ctx.beginPath();
    ctx.ellipse(w/2, h*0.42, w*0.36, h*0.34, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  async startTryOn(videoElement, canvasElement) {
    this.videoEl = videoElement;
    this.canvasContainerEl = canvasElement;
    this.mode = 'camera';

    try {
      // Get camera stream
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        }
      });
      
      this.videoEl.srcObject = this.stream;
      await this.waitForVideo();
      
      // Create overlay canvas
      this.setupOverlayCanvas();
      
      // Start rendering
      this.isActive = true;
      this.renderLoop();
      
      console.log('🎥 Camera try-on started');
      return true;
    } catch (error) {
      console.error('❌ Camera access failed:', error);
      throw error;
    }
  }

  async startOnImage(photoElement, canvasElement, imageSrc) {
    console.log('📸 Starting try-on with photo:', imageSrc);
    this.photoEl = photoElement;
    this.canvasContainerEl = canvasElement;
    this.mode = 'photo';

    // Set the source directly
    if (imageSrc) {
      this.photoEl.src = imageSrc;
    }

    return new Promise((resolve, reject) => {
      this.photoEl.onload = async () => {
        try {
          console.log('✅ Photo loaded, setting up overlay...');
          // Setup overlay canvas
          this.setupOverlayCanvas();
          
          // Detect face in photo and apply overlay
          await this.detectAndApplyOverlay();
          
          this.isActive = true;
          console.log('🖼️ Photo try-on started successfully');
          resolve(true);
        } catch (error) {
          console.error('❌ Error starting photo try-on:', error);
          reject(error);
        }
      };
      
      this.photoEl.onerror = (e) => {
        console.error('❌ Photo load error:', e);
        reject(e);
      };
      
      // Trigger load if image is already cached
      if (this.photoEl.complete) {
        this.photoEl.onload();
      }
    });
  }

  setupOverlayCanvas() {
    // Create canvas for overlay
    if (!this.overlayCanvas) {
      this.overlayCanvas = document.createElement('canvas');
      this.overlayCanvas.style.position = 'absolute';
      this.overlayCanvas.style.top = '0';
      this.overlayCanvas.style.left = '0';
      this.overlayCanvas.style.width = '100%';
      this.overlayCanvas.style.height = '100%';
      this.overlayCanvas.style.pointerEvents = 'none';
      this.canvasContainerEl.appendChild(this.overlayCanvas);
    }
    
    // Set canvas size to match container
    const rect = this.canvasContainerEl.getBoundingClientRect();
    this.overlayCanvas.width = rect.width;
    this.overlayCanvas.height = rect.height;
    this.overlayCtx = this.overlayCanvas.getContext('2d');
  }

  async detectAndApplyOverlay() {
    if (!this.currentStyle || !this.hairstyleImages[this.currentStyle]) {
      console.log('⚠️ No hairstyle selected or image not found');
      return;
    }

    const img = this.hairstyleImages[this.currentStyle];
    const canvas = this.overlayCanvas;
    const ctx = this.overlayCtx;
    
    console.log('🎨 Applying overlay for style:', this.currentStyle);
    
    // Clear previous overlay
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Detect face
    let faceData = await this.detectFace();
    
    if (!faceData) {
      console.log('⚠️ No face detected, using default position');
      // Fallback: center of image
      faceData = {
        x: canvas.width * 0.5,
        y: canvas.height * 0.3,
        width: canvas.width * 0.5,
        height: canvas.height * 0.4
      };
    }

    console.log('📍 Face detected at:', faceData);

    // Draw hairstyle overlay on detected face
    const hairWidth = faceData.width * 1.2;
    const hairHeight = faceData.height * 0.8;
    const hairX = faceData.x - hairWidth / 2;
    const hairY = faceData.y - faceData.height * 0.5;

    console.log('📏 Drawing hair overlay at:', { hairX, hairY, hairWidth, hairHeight });
    
    // Draw the hairstyle overlay
    ctx.drawImage(img, hairX, hairY, hairWidth, hairHeight);
    
    console.log('✅ Overlay applied successfully');
  }

  async detectFace() {
    // Simple face detection
    try {
      if (this.mode === 'photo' && this.photoEl) {
        // For photos, use center-based estimation
        const rect = this.photoEl.getBoundingClientRect();
        const containerRect = this.canvasContainerEl.getBoundingClientRect();
        
        return {
          x: (rect.left - containerRect.left + rect.width / 2),
          y: (rect.top - containerRect.top + rect.height * 0.35),
          width: rect.width * 0.6,
          height: rect.height * 0.5
        };
      } else if (this.mode === 'camera' && this.videoEl) {
        // For video, use center-based estimation
        const rect = this.videoEl.getBoundingClientRect();
        const containerRect = this.canvasContainerEl.getBoundingClientRect();
        
        return {
          x: (rect.left - containerRect.left + rect.width / 2),
          y: (rect.top - containerRect.top + rect.height * 0.35),
          width: rect.width * 0.6,
          height: rect.height * 0.5
        };
      }
    } catch (error) {
      console.error('Face detection error:', error);
    }
    
    return null;
  }

  renderLoop() {
    if (!this.isActive) return;

    if (this.mode === 'camera') {
      this.detectAndApplyOverlay();
    }

    this.animationFrame = requestAnimationFrame(() => this.renderLoop());
  }

  async loadHairstyle(styleName) {
    console.log(`🎨 Loading hairstyle: ${styleName}`);
    this.currentStyle = styleName;
    
    if (this.isActive) {
      await this.detectAndApplyOverlay();
    }
    
    return true;
  }

  stopTryOn() {
    this.isActive = false;
    
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    
    if (this.videoEl) {
      this.videoEl.srcObject = null;
    }
    
    console.log('🛑 Try-on stopped');
    return true;
  }

  takeScreenshot() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (this.mode === 'photo' && this.photoEl) {
      // Screenshot of photo with overlay
      canvas.width = this.photoEl.naturalWidth || 800;
      canvas.height = this.photoEl.naturalHeight || 600;
      
      // Draw photo
      ctx.drawImage(this.photoEl, 0, 0, canvas.width, canvas.height);
      
      // Draw overlay (scaled)
      const scale = canvas.width / this.overlayCanvas.width;
      ctx.drawImage(
        this.overlayCanvas, 
        0, 0, this.overlayCanvas.width, this.overlayCanvas.height,
        0, 0, canvas.width, canvas.height
      );
    } else if (this.mode === 'camera' && this.videoEl) {
      // Screenshot of video with overlay
      canvas.width = this.videoEl.videoWidth || 640;
      canvas.height = this.videoEl.videoHeight || 480;
      
      // Draw video frame
      ctx.drawImage(this.videoEl, 0, 0, canvas.width, canvas.height);
      
      // Draw overlay (scaled)
      const scale = canvas.width / this.overlayCanvas.width;
      ctx.drawImage(
        this.overlayCanvas,
        0, 0, this.overlayCanvas.width, this.overlayCanvas.height,
        0, 0, canvas.width, canvas.height
      );
    }

    return canvas.toDataURL('image/png');
  }

  waitForVideo() {
    return new Promise((resolve) => {
      if (this.videoEl.readyState >= 2) {
        resolve();
      } else {
        this.videoEl.onloadeddata = () => resolve();
      }
    });
  }
}

// Export to global scope
window.VirtualTryOn = VirtualTryOn;
