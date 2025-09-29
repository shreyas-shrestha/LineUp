"use strict";

(function(){
  class VirtualTryOn {
    constructor() {
      this.stream = null;
      this.videoEl = null;
      this.canvasContainerEl = null; // DOM container for overlay elements
      this.overlayImgEl = null;
      this.overlay = {
        x: 0,
        y: 0,
        scale: 1,
        rotation: 0,
        src: null,
        naturalWidth: 400,
        naturalHeight: 250
      };
      this.isInitialized = false;
      this.dragging = false;
      this.dragOffset = { x: 0, y: 0 };
      this.keydownHandler = null;
      this.wheelHandler = null;
      this.pointerDownHandler = null;
      this.pointerMoveHandler = null;
      this.pointerUpHandler = null;
      this.touchStartHandler = null;
      this.touchMoveHandler = null;
      this.touchEndHandler = null;
      this.activePointers = new Map();
      this.mode = 'camera';
      this.photoEl = null;
    }

    async initialize() {
      // Nothing heavy to initialize yet; placeholder for future ML models
      this.isInitialized = true;
      return true;
    }

    async startTryOn(videoElement, canvasElement) {
      this.videoEl = videoElement;
      this.canvasContainerEl = canvasElement;
      this.mode = 'camera';

      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      } catch (e) {
        console.error("Camera access failed:", e);
        throw e;
      }

      this.videoEl.srcObject = this.stream;
      await this._waitForVideo(this.videoEl);

      // Ensure overlay element exists
      this._ensureOverlayElement();

      // Default overlay position centered
      const { width, height } = this._containerSize();
      this.overlay.x = width / 2;
      this.overlay.y = height * 0.35; // near top third
      this.overlay.scale = Math.min(width / this.overlay.naturalWidth, height / this.overlay.naturalHeight) * 0.8;
      this.overlay.rotation = 0;
      this._updateOverlayTransform();

      // Attach interactions
      this._attachInteractions();

      return true;
    }

    async startOnImage(photoElement, canvasElement, src) {
      this.photoEl = photoElement;
      this.canvasContainerEl = canvasElement;
      this.mode = 'photo';

      return new Promise((resolve, reject) => {
        const onLoad = async () => {
          // Ensure overlay element exists
          this._ensureOverlayElement();
          // Default overlay position centered relative to container
          const { width, height } = this._containerSize();
          this.overlay.x = width / 2;
          this.overlay.y = height * 0.35;
          this.overlay.scale = Math.min(width / this.overlay.naturalWidth, height / this.overlay.naturalHeight) * 0.8;
          this.overlay.rotation = 0;

          // Progressive enhancement: auto-fit using FaceDetector if available
          try {
            if ('FaceDetector' in window) {
              const detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
              const faces = await detector.detect(this.photoEl);
              if (faces && faces.length > 0) {
                const box = faces[0].boundingBox; // {x,y,width,height} in CSS pixels
                // Position overlay centered above face box
                const rect = this.canvasContainerEl.getBoundingClientRect();
                const imgRect = this.photoEl.getBoundingClientRect();
                const centerX = (box.x + box.width / 2) - (imgRect.left - rect.left);
                const topY = box.y - (imgRect.top - rect.top);
                this.overlay.x = centerX;
                this.overlay.y = topY + box.height * 0.15; // a little above center
                // Scale overlay width roughly to face width * factor
                const targetW = box.width * 1.6; // hair wider than face
                this.overlay.scale = targetW / this.overlay.naturalWidth;
              }
            }
          } catch (e) {
            // Ignore detection errors; keep defaults
          }

          this._updateOverlayTransform();
          this._attachInteractions();
          resolve(true);
        };
        this.photoEl.onload = onLoad;
        this.photoEl.onerror = (e) => reject(e);
        this.photoEl.src = src;
      });
    }

    stopTryOn() {
      if (this.stream) {
        this.stream.getTracks().forEach(t => t.stop());
      }
      if (this.videoEl) {
        this.videoEl.srcObject = null;
      }
      this._detachInteractions();
      return true;
    }

    async loadHairstyle(styleName) {
      const dataUrl = this._generateOverlayForStyle(styleName);
      if (!this.overlayImgEl) this._ensureOverlayElement();

      return new Promise((resolve) => {
        this.overlayImgEl.onload = () => {
          this.overlay.naturalWidth = this.overlayImgEl.naturalWidth || 400;
          this.overlay.naturalHeight = this.overlayImgEl.naturalHeight || 250;
          this.overlay.src = dataUrl;
          // Recompute scale to fit width
          const { width, height } = this._containerSize();
          this.overlay.scale = Math.min(width / this.overlay.naturalWidth, height / this.overlay.naturalHeight) * 0.8;
          this._updateOverlayTransform();
          resolve(true);
        };
        this.overlayImgEl.src = dataUrl;
      });
    }

    takeScreenshot() {
      let canvas = document.createElement('canvas');
      let ctx = canvas.getContext('2d');

      if (this.mode === 'photo' && this.photoEl) {
        const width = this.photoEl.naturalWidth || 800;
        const height = this.photoEl.naturalHeight || 800;
        canvas.width = width;
        canvas.height = height;
        // Draw the uploaded photo
        ctx.drawImage(this.photoEl, 0, 0, width, height);

        if (this.overlayImgEl && this.overlayImgEl.complete) {
          const dom = this.canvasContainerEl.getBoundingClientRect();
          const photoDom = this.photoEl.getBoundingClientRect();
          const sx = width / photoDom.width;
          const sy = height / photoDom.height;
          const centerXDom = this.overlay.x + (photoDom.left - dom.left);
          const centerYDom = this.overlay.y + (photoDom.top - dom.top);
          const centerX = (centerXDom - photoDom.left) * sx;
          const centerY = (centerYDom - photoDom.top) * sy;
          const drawW = this.overlay.naturalWidth * this.overlay.scale * sx;
          const drawH = this.overlay.naturalHeight * this.overlay.scale * sy;
          ctx.save();
          ctx.translate(centerX, centerY);
          ctx.rotate(this.overlay.rotation);
          ctx.drawImage(this.overlayImgEl, -drawW / 2, -drawH / 2, drawW, drawH);
          ctx.restore();
        }
      } else {
        // camera mode
        const { width, height } = this._videoSize();
        canvas.width = width;
        canvas.height = height;
        // Draw the current video frame
        ctx.drawImage(this.videoEl, 0, 0, width, height);
        if (this.overlayImgEl && this.overlayImgEl.complete) {
          const dom = this.canvasContainerEl.getBoundingClientRect();
          const videoDom = this.videoEl.getBoundingClientRect();
          const sx = width / videoDom.width;
          const sy = height / videoDom.height;
          const centerXDom = this.overlay.x + (videoDom.left - dom.left);
          const centerYDom = this.overlay.y + (videoDom.top - dom.top);
          const centerX = (centerXDom - videoDom.left) * sx;
          const centerY = (centerYDom - videoDom.top) * sy;
          const drawW = this.overlay.naturalWidth * this.overlay.scale * sx;
          const drawH = this.overlay.naturalHeight * this.overlay.scale * sy;
          ctx.save();
          ctx.translate(centerX, centerY);
          ctx.rotate(this.overlay.rotation);
          ctx.drawImage(this.overlayImgEl, -drawW / 2, -drawH / 2, drawW, drawH);
          ctx.restore();
        }
      }

      return canvas.toDataURL('image/png');
    }

    // --- Internals ---
    _ensureOverlayElement() {
      if (this.overlayImgEl) return;
      const img = document.createElement('img');
      img.alt = 'Try-On Overlay';
      img.style.position = 'absolute';
      img.style.left = '0';
      img.style.top = '0';
      img.style.willChange = 'transform';
      img.style.userSelect = 'none';
      img.style.pointerEvents = 'auto';
      img.draggable = false;
      this.canvasContainerEl.appendChild(img);
      this.overlayImgEl = img;
    }

    _updateOverlayTransform() {
      if (!this.overlayImgEl) return;
      const w = this.overlay.naturalWidth * this.overlay.scale;
      const h = this.overlay.naturalHeight * this.overlay.scale;
      // translate uses px in container space
      this.overlayImgEl.style.width = `${w}px`;
      this.overlayImgEl.style.height = `${h}px`;
      this.overlayImgEl.style.transform = `translate(${this.overlay.x - w/2}px, ${this.overlay.y - h/2}px) rotate(${this.overlay.rotation}rad)`;
    }

    _attachInteractions() {
      // Wheel to scale
      this.wheelHandler = (e) => {
        e.preventDefault();
        const delta = e.deltaY;
        const factor = delta > 0 ? 0.95 : 1.05;
        this.overlay.scale = Math.max(0.1, Math.min(5, this.overlay.scale * factor));
        this._updateOverlayTransform();
      };
      this.canvasContainerEl.addEventListener('wheel', this.wheelHandler, { passive: false });

      // Pointer drag on overlay only
      this.pointerDownHandler = (e) => {
        if (e.target !== this.overlayImgEl) return;
        e.preventDefault();
        this.dragging = true;
        const rect = this.canvasContainerEl.getBoundingClientRect();
        const w = this.overlay.naturalWidth * this.overlay.scale;
        const h = this.overlay.naturalHeight * this.overlay.scale;
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        this.dragOffset.x = clickX - (this.overlay.x);
        this.dragOffset.y = clickY - (this.overlay.y);
      };

      this.pointerMoveHandler = (e) => {
        if (!this.dragging) return;
        const rect = this.canvasContainerEl.getBoundingClientRect();
        const x = e.clientX - rect.left - this.dragOffset.x;
        const y = e.clientY - rect.top - this.dragOffset.y;
        this.overlay.x = x;
        this.overlay.y = y;
        this._updateOverlayTransform();
      };

      this.pointerUpHandler = () => {
        this.dragging = false;
      };

      this.canvasContainerEl.addEventListener('pointerdown', this.pointerDownHandler);
      window.addEventListener('pointermove', this.pointerMoveHandler);
      window.addEventListener('pointerup', this.pointerUpHandler);

      // Touch pinch/rotate (basic two-finger scale + rotation)
      this.touchStartHandler = (e) => {
        for (const t of e.changedTouches) this.activePointers.set(t.identifier, { x: t.clientX, y: t.clientY });
      };
      this.touchMoveHandler = (e) => {
        if (this.activePointers.size >= 2) {
          const pts = Array.from(this.activePointers.values());
          const t1 = e.touches[0];
          const t2 = e.touches[1];
          const prevDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
          const prevAngle = Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x);
          const curDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
          const curAngle = Math.atan2(t2.clientY - t1.clientY, t2.clientX - t1.clientX);
          const scaleFactor = curDist / (prevDist || curDist);
          this.overlay.scale = Math.max(0.1, Math.min(5, this.overlay.scale * scaleFactor));
          const angleDelta = curAngle - prevAngle;
          this.overlay.rotation += angleDelta;
          this._updateOverlayTransform();
          // Update stored pointers
          this.activePointers.set(e.touches[0].identifier, { x: t1.clientX, y: t1.clientY });
          this.activePointers.set(e.touches[1].identifier, { x: t2.clientX, y: t2.clientY });
          e.preventDefault();
        }
      };
      this.touchEndHandler = (e) => {
        for (const t of e.changedTouches) this.activePointers.delete(t.identifier);
      };
      this.canvasContainerEl.addEventListener('touchstart', this.touchStartHandler, { passive: false });
      this.canvasContainerEl.addEventListener('touchmove', this.touchMoveHandler, { passive: false });
      this.canvasContainerEl.addEventListener('touchend', this.touchEndHandler);
      this.canvasContainerEl.addEventListener('touchcancel', this.touchEndHandler);

      // Keyboard rotate: Q/E
      this.keydownHandler = (e) => {
        if (e.key === 'q' || e.key === 'Q') {
          this.overlay.rotation -= 0.05;
          this._updateOverlayTransform();
        }
        if (e.key === 'e' || e.key === 'E') {
          this.overlay.rotation += 0.05;
          this._updateOverlayTransform();
        }
      };
      window.addEventListener('keydown', this.keydownHandler);
    }

    _detachInteractions() {
      if (this.wheelHandler) this.canvasContainerEl.removeEventListener('wheel', this.wheelHandler);
      if (this.pointerDownHandler) this.canvasContainerEl.removeEventListener('pointerdown', this.pointerDownHandler);
      if (this.pointerMoveHandler) window.removeEventListener('pointermove', this.pointerMoveHandler);
      if (this.pointerUpHandler) window.removeEventListener('pointerup', this.pointerUpHandler);
      if (this.touchStartHandler) this.canvasContainerEl.removeEventListener('touchstart', this.touchStartHandler);
      if (this.touchMoveHandler) this.canvasContainerEl.removeEventListener('touchmove', this.touchMoveHandler);
      if (this.touchEndHandler) {
        this.canvasContainerEl.removeEventListener('touchend', this.touchEndHandler);
        this.canvasContainerEl.removeEventListener('touchcancel', this.touchEndHandler);
      }
      if (this.keydownHandler) window.removeEventListener('keydown', this.keydownHandler);
      this.activePointers.clear();
      this.dragging = false;
    }

    _waitForVideo(video) {
      return new Promise((resolve) => {
        if (video.readyState >= 2) return resolve();
        video.onloadeddata = () => resolve();
      });
    }

    _containerSize() {
      const rect = this.canvasContainerEl.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    }

    _videoSize() {
      const vw = this.videoEl.videoWidth || 640;
      const vh = this.videoEl.videoHeight || 480;
      return { width: vw, height: vh };
    }

    _generateOverlayForStyle(styleName) {
      // Procedurally generate a semi-transparent overlay to simulate hair shape
      const w = 500, h = 300;
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const ctx = c.getContext('2d');

      // Choose a color based on style name hash
      const colors = [
        ['#c084fc', '#60a5fa'], // purple -> blue
        ['#f472b6', '#f59e0b'], // pink -> amber
        ['#34d399', '#10b981'], // emerald
        ['#f43f5e', '#f97316'], // rose -> orange
        ['#a78bfa', '#38bdf8']  // violet -> sky
      ];
      let hash = 0;
      for (let i = 0; i < styleName.length; i++) hash = (hash * 31 + styleName.charCodeAt(i)) >>> 0;
      const palette = colors[hash % colors.length];

      // Background transparent
      ctx.clearRect(0, 0, w, h);

      // Hair cap (ellipse)
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, palette[0] + 'CC');
      grad.addColorStop(1, palette[1] + 'CC');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(w/2, h*0.55, w*0.42, h*0.55, 0, 0, Math.PI * 2);
      ctx.fill();

      // Fringe
      ctx.fillStyle = 'rgba(0,0,0,0.08)';
      for (let i = 0; i < 6; i++) {
        ctx.beginPath();
        const x = w/2 - 120 + i * 48;
        ctx.ellipse(x, h*0.35 + (i%2)*6, 24, 40, 0.2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Label (style name)
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.font = 'bold 28px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(styleName, w/2, h - 18);

      return c.toDataURL('image/png');
    }
  }

  // Expose globally
  window.VirtualTryOn = VirtualTryOn;
})();

// virtual-tryon.js - AR Virtual Hairstyle Try-On Implementation for LineUp
// Uses MediaPipe for face detection + Three.js for 3D hairstyle overlay

class VirtualTryOn {
    constructor() {
        this.camera = null;
        this.faceMesh = null;
        this.scene = null;
        this.renderer = null;
        this.camera3d = null;
        this.currentHairstyle = null;
        this.isActive = false;
        
        // MediaPipe Face Mesh configuration
        this.faceMeshConfig = {
            locateFile: (file) => {
                return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
            }
        };
        
        // Available hairstyle models (3D assets)
        this.hairstyleModels = {
            'Modern Fade': '/models/modern-fade.glb',
            'Classic Pompadour': '/models/pompadour.glb',
            'Textured Quiff': '/models/quiff.glb',
            'Messy Crop': '/models/crop.glb',
            'Buzz Cut': '/models/buzz.glb'
        };
    }

    // Initialize the virtual try-on system
    async initialize() {
        try {
            console.log('🎭 Initializing Virtual Try-On...');
            
            // Initialize MediaPipe Face Mesh
            await this.initializeFaceMesh();
            
            // Initialize Three.js scene
            this.initializeThreeJS();
            
            // Setup camera stream
            await this.initializeCamera();
            
            console.log('✅ Virtual Try-On initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Virtual Try-On initialization failed:', error);
            return false;
        }
    }

    // Initialize MediaPipe Face Mesh for face landmark detection
    async initializeFaceMesh() {
        return new Promise((resolve, reject) => {
            this.faceMesh = new window.FaceMesh(this.faceMeshConfig);
            
            this.faceMesh.setOptions({
                maxNumFaces: 1,
                refineLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            this.faceMesh.onResults((results) => {
                this.onFaceMeshResults(results);
            });

            // Wait for MediaPipe to load
            setTimeout(() => resolve(), 1000);
        });
    }

    // Initialize Three.js for 3D rendering
    initializeThreeJS() {
        // Create scene
        this.scene = new THREE.Scene();
        
        // Create camera
        this.camera3d = new THREE.PerspectiveCamera(75, 640 / 480, 0.1, 1000);
        this.camera3d.position.z = 5;
        
        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ 
            alpha: true,
            antialias: true
        });
        this.renderer.setSize(640, 480);
        this.renderer.setClearColor(0x000000, 0); // Transparent background
        
        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 1, 1);
        this.scene.add(directionalLight);
    }

    // Initialize camera stream
    async initializeCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            
            this.camera = stream;
            return stream;
        } catch (error) {
            throw new Error('Failed to access camera: ' + error.message);
        }
    }

    // Process face mesh detection results
    onFaceMeshResults(results) {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            const landmarks = results.multiFaceLandmarks[0];
            this.updateHairstylePosition(landmarks);
        }
    }

    // Update 3D hairstyle position based on face landmarks
    updateHairstylePosition(landmarks) {
        if (!this.currentHairstyle) return;

        // Key facial landmarks for hairstyle positioning
        const foreheadCenter = landmarks[9];   // Center of forehead
        const leftTemple = landmarks[127];     // Left temple
        const rightTemple = landmarks[356];    // Right temple
        const chinCenter = landmarks[175];     // Center of chin

        // Calculate head position and rotation
        const headWidth = Math.abs(leftTemple.x - rightTemple.x);
        const headHeight = Math.abs(foreheadCenter.y - chinCenter.y);
        
        // Update hairstyle position
        this.currentHairstyle.position.set(
            (foreheadCenter.x - 0.5) * 10, // X position
            (0.5 - foreheadCenter.y) * 10 + 2, // Y position (above forehead)
            -2 // Z position
        );
        
        // Scale based on head size
        const scale = headWidth * 15;
        this.currentHairstyle.scale.set(scale, scale, scale);
        
        // Rotate based on head tilt
        const headTilt = Math.atan2(rightTemple.y - leftTemple.y, rightTemple.x - leftTemple.x);
        this.currentHairstyle.rotation.z = -headTilt;
    }

    // Load and display a specific hairstyle
    async loadHairstyle(styleName) {
        try {
            console.log(`🎨 Loading hairstyle: ${styleName}`);
            
            // Remove current hairstyle
            if (this.currentHairstyle) {
                this.scene.remove(this.currentHairstyle);
            }
            
            // Load new hairstyle model
            const modelPath = this.hairstyleModels[styleName];
            if (!modelPath) {
                throw new Error(`Hairstyle model not found: ${styleName}`);
            }
            
            const loader = new THREE.GLTFLoader();
            const gltf = await new Promise((resolve, reject) => {
                loader.load(modelPath, resolve, undefined, reject);
            });
            
            this.currentHairstyle = gltf.scene;
            this.scene.add(this.currentHairstyle);
            
            console.log(`✅ Hairstyle loaded: ${styleName}`);
            return true;
        } catch (error) {
            console.error(`❌ Failed to load hairstyle: ${error.message}`);
            return false;
        }
    }

    // Start the virtual try-on session
    async startTryOn(videoElement, canvasElement) {
        if (this.isActive) return;
        
        try {
            // Set up video stream
            videoElement.srcObject = this.camera;
            await videoElement.play();
            
            // Set up rendering canvas
            canvasElement.appendChild(this.renderer.domElement);
            
            this.isActive = true;
            
            // Start the rendering loop
            this.renderLoop(videoElement);
            
            console.log('🎥 Virtual Try-On session started');
            return true;
        } catch (error) {
            console.error('❌ Failed to start try-on session:', error);
            return false;
        }
    }

    // Main rendering loop
    renderLoop(videoElement) {
        if (!this.isActive) return;
        
        // Process current video frame with MediaPipe
        if (videoElement && videoElement.videoWidth > 0) {
            this.faceMesh.send({ image: videoElement });
        }
        
        // Render 3D scene
        this.renderer.render(this.scene, this.camera3d);
        
        // Continue loop
        requestAnimationFrame(() => this.renderLoop(videoElement));
    }

    // Stop the virtual try-on session
    stopTryOn() {
        this.isActive = false;
        
        if (this.camera) {
            this.camera.getTracks().forEach(track => track.stop());
        }
        
        console.log('🛑 Virtual Try-On session stopped');
    }

    // Take a screenshot of the current try-on
    takeScreenshot() {
        if (!this.renderer) return null;
        
        return this.renderer.domElement.toDataURL('image/png');
    }

    // Cleanup resources
    cleanup() {
        this.stopTryOn();
        
        if (this.renderer) {
            this.renderer.dispose();
        }
        
        if (this.scene) {
            this.scene.clear();
        }
        
        console.log('🧹 Virtual Try-On cleaned up');
    }
}

// Export for use in main application
window.VirtualTryOn = VirtualTryOn;