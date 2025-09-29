// virtual-tryon-fixed.js - Simplified AR Virtual Try-On for LineUp
"use strict";

class VirtualTryOn {
    constructor() {
        this.stream = null;
        this.videoEl = null;
        this.canvasEl = null;
        this.photoEl = null;
        this.overlayEl = null;
        this.mode = 'camera'; // 'camera' or 'photo'
        this.isActive = false;
        this.currentStyle = null;
        this.currentColor = null;
        
        // Overlay positioning
        this.overlay = {
            x: 320,
            y: 150,
            scale: 1.0,
            rotation: 0,
            width: 300,
            height: 200
        };
        
        // Interaction state
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        
        // Event handlers stored for cleanup
        this.handlers = {};
    }

    async initialize() {
        console.log('🎭 Initializing Virtual Try-On...');
        this.isActive = true;
        return true;
    }

    async startTryOn(videoElement, canvasElement) {
        try {
            this.videoEl = videoElement;
            this.canvasEl = canvasElement;
            this.mode = 'camera';
            
            // Get camera stream
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            this.videoEl.srcObject = this.stream;
            await this.waitForVideo();
            
            // Setup overlay
            this.setupOverlay();
            this.attachInteractions();
            
            console.log('✅ Camera try-on started');
            return true;
        } catch (error) {
            console.error('❌ Failed to start camera:', error);
            throw error;
        }
    }

    async startOnImage(photoElement, canvasElement, imageSrc) {
        try {
            this.photoEl = photoElement;
            this.canvasEl = canvasElement;
            this.mode = 'photo';
            
            // Load image
            await new Promise((resolve, reject) => {
                this.photoEl.onload = resolve;
                this.photoEl.onerror = reject;
                this.photoEl.src = imageSrc;
            });
            
            // Setup overlay
            this.setupOverlay();
            this.attachInteractions();
            
            console.log('✅ Photo try-on started');
            return true;
        } catch (error) {
            console.error('❌ Failed to load photo:', error);
            throw error;
        }
    }

    setupOverlay() {
        // Get or create overlay element
        this.overlayEl = document.getElementById('hairstyle-overlay');
        if (!this.overlayEl) {
            this.overlayEl = document.createElement('img');
            this.overlayEl.id = 'hairstyle-overlay';
            this.overlayEl.className = 'ar-overlay';
            this.overlayEl.style.pointerEvents = 'auto';
            
            const container = this.canvasEl.parentElement;
            container.appendChild(this.overlayEl);
        }
        
        // Set initial position
        this.resetPosition();
        this.updateOverlayTransform();
    }

    resetPosition() {
        const container = this.canvasEl.parentElement;
        const rect = container.getBoundingClientRect();
        
        this.overlay = {
            x: rect.width / 2,
            y: rect.height * 0.3, // Position near top of head
            scale: 1.0,
            rotation: 0,
            width: 300,
            height: 200
        };
    }

    updateOverlayTransform() {
        if (!this.overlayEl) return;
        
        const width = this.overlay.width * this.overlay.scale;
        const height = this.overlay.height * this.overlay.scale;
        
        this.overlayEl.style.width = `${width}px`;
        this.overlayEl.style.height = `${height}px`;
        this.overlayEl.style.transform = `
            translate(${this.overlay.x - width/2}px, ${this.overlay.y - height/2}px)
            rotate(${this.overlay.rotation}deg)
        `;
    }

    async loadHairstyle(styleName) {
        this.currentStyle = styleName;
        
        // Generate hairstyle overlay
        const dataUrl = this.generateHairstyleOverlay(styleName, this.currentColor);
        
        if (this.overlayEl) {
            await new Promise(resolve => {
                this.overlayEl.onload = resolve;
                this.overlayEl.src = dataUrl;
                this.overlayEl.classList.remove('hidden');
            });
        }
        
        console.log(`✨ Loaded hairstyle: ${styleName}`);
        return true;
    }

    generateHairstyleOverlay(styleName, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 600;
        canvas.height = 400;
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Choose color based on selection or style
        let hairColor = color || this.getStyleColor(styleName);
        
        // Create gradient for more realistic look
        const gradient = ctx.createRadialGradient(
            canvas.width/2, canvas.height/2, 50,
            canvas.width/2, canvas.height/2, 200
        );
        gradient.addColorStop(0, hairColor + 'FF');
        gradient.addColorStop(0.5, hairColor + 'CC');
        gradient.addColorStop(1, hairColor + '88');
        
        // Draw hairstyle shape based on style name
        ctx.fillStyle = gradient;
        ctx.strokeStyle = hairColor + '66';
        ctx.lineWidth = 2;
        
        this.drawHairstyleShape(ctx, styleName, canvas.width, canvas.height);
        
        // Add style label
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.font = 'bold 24px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 4;
        ctx.fillText(styleName, canvas.width/2, canvas.height - 20);
        
        return canvas.toDataURL('image/png');
    }

    drawHairstyleShape(ctx, styleName, width, height) {
        const centerX = width / 2;
        const centerY = height / 2;
        
        ctx.beginPath();
        
        switch(styleName.toLowerCase()) {
            case 'modern fade':
            case 'classic fade':
                // Fade shape - shorter on sides
                ctx.ellipse(centerX, centerY, width * 0.35, height * 0.4, 0, 0, Math.PI * 2);
                ctx.fill();
                // Add texture lines
                for (let i = 0; i < 5; i++) {
                    ctx.beginPath();
                    ctx.moveTo(centerX - 100 + i * 50, centerY - 80);
                    ctx.quadraticCurveTo(centerX - 100 + i * 50, centerY - 40, centerX - 80 + i * 50, centerY);
                    ctx.stroke();
                }
                break;
                
            case 'textured quiff':
            case 'pompadour':
                // Quiff shape - volume at front
                ctx.moveTo(centerX - 150, centerY + 50);
                ctx.quadraticCurveTo(centerX - 150, centerY - 100, centerX, centerY - 120);
                ctx.quadraticCurveTo(centerX + 150, centerY - 100, centerX + 150, centerY + 50);
                ctx.quadraticCurveTo(centerX, centerY + 100, centerX - 150, centerY + 50);
                ctx.fill();
                break;
                
            case 'messy crop':
                // Messy texture
                for (let i = 0; i < 8; i++) {
                    const angle = (Math.PI * 2 * i) / 8;
                    const x = centerX + Math.cos(angle) * 120;
                    const y = centerY + Math.sin(angle) * 80;
                    ctx.beginPath();
                    ctx.ellipse(x, y, 40, 60, angle, 0, Math.PI * 2);
                    ctx.fill();
                }
                break;
                
            case 'buzz cut':
                // Very short all over
                ctx.ellipse(centerX, centerY, width * 0.38, height * 0.45, 0, 0, Math.PI * 2);
                ctx.fill();
                // Add dot texture for short hair
                ctx.fillStyle = ctx.fillStyle.replace('FF', '44');
                for (let x = -150; x < 150; x += 15) {
                    for (let y = -100; y < 100; y += 15) {
                        if (Math.sqrt(x*x/(150*150) + y*y/(100*100)) < 1) {
                            ctx.fillRect(centerX + x, centerY + y, 3, 3);
                        }
                    }
                }
                break;
                
            default:
                // Default oval shape
                ctx.ellipse(centerX, centerY, width * 0.4, height * 0.45, 0, 0, Math.PI * 2);
                ctx.fill();
        }
        
        ctx.closePath();
    }

    getStyleColor(styleName) {
        // Generate color based on style name hash
        const colors = [
            '#2c1810', // Dark brown
            '#4a2c17', // Medium brown  
            '#8b4513', // Saddle brown
            '#1a1a1a', // Near black
            '#6b4423'  // Light brown
        ];
        
        let hash = 0;
        for (let i = 0; i < styleName.length; i++) {
            hash = (hash * 31 + styleName.charCodeAt(i)) >>> 0;
        }
        
        return colors[hash % colors.length];
    }

    changeColor(color) {
        this.currentColor = color;
        if (this.currentStyle) {
            this.loadHairstyle(this.currentStyle);
        }
    }

    attachInteractions() {
        const container = this.canvasEl.parentElement;
        
        // Mouse/touch drag
        this.handlers.mousedown = (e) => this.handleDragStart(e);
        this.handlers.mousemove = (e) => this.handleDragMove(e);
        this.handlers.mouseup = (e) => this.handleDragEnd(e);
        this.handlers.touchstart = (e) => this.handleDragStart(e.touches[0]);
        this.handlers.touchmove = (e) => this.handleDragMove(e.touches[0]);
        this.handlers.touchend = (e) => this.handleDragEnd(e);
        
        // Wheel for scale
        this.handlers.wheel = (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.95 : 1.05;
            this.overlay.scale = Math.max(0.3, Math.min(3, this.overlay.scale * delta));
            this.updateOverlayTransform();
        };
        
        // Keyboard rotation
        this.handlers.keydown = (e) => {
            if (e.key === 'q' || e.key === 'Q') {
                this.overlay.rotation -= 5;
                this.updateOverlayTransform();
            } else if (e.key === 'e' || e.key === 'E') {
                this.overlay.rotation += 5;
                this.updateOverlayTransform();
            }
        };
        
        // Attach all handlers
        if (this.overlayEl) {
            this.overlayEl.addEventListener('mousedown', this.handlers.mousedown);
            this.overlayEl.addEventListener('touchstart', this.handlers.touchstart, { passive: false });
        }
        window.addEventListener('mousemove', this.handlers.mousemove);
        window.addEventListener('mouseup', this.handlers.mouseup);
        window.addEventListener('touchmove', this.handlers.touchmove, { passive: false });
        window.addEventListener('touchend', this.handlers.touchend);
        container.addEventListener('wheel', this.handlers.wheel, { passive: false });
        window.addEventListener('keydown', this.handlers.keydown);
    }

    handleDragStart(e) {
        if (e.target !== this.overlayEl) return;
        e.preventDefault();
        
        this.isDragging = true;
        const rect = this.canvasEl.parentElement.getBoundingClientRect();
        this.dragOffset = {
            x: e.clientX - rect.left - this.overlay.x,
            y: e.clientY - rect.top - this.overlay.y
        };
    }

    handleDragMove(e) {
        if (!this.isDragging) return;
        e.preventDefault();
        
        const rect = this.canvasEl.parentElement.getBoundingClientRect();
        this.overlay.x = e.clientX - rect.left - this.dragOffset.x;
        this.overlay.y = e.clientY - rect.top - this.dragOffset.y;
        this.updateOverlayTransform();
    }

    handleDragEnd(e) {
        this.isDragging = false;
    }

    detachInteractions() {
        // Remove all event handlers
        if (this.overlayEl) {
            this.overlayEl.removeEventListener('mousedown', this.handlers.mousedown);
            this.overlayEl.removeEventListener('touchstart', this.handlers.touchstart);
        }
        window.removeEventListener('mousemove', this.handlers.mousemove);
        window.removeEventListener('mouseup', this.handlers.mouseup);
        window.removeEventListener('touchmove', this.handlers.touchmove);
        window.removeEventListener('touchend', this.handlers.touchend);
        
        const container = this.canvasEl?.parentElement;
        if (container) {
            container.removeEventListener('wheel', this.handlers.wheel);
        }
        window.removeEventListener('keydown', this.handlers.keydown);
    }

    async switchCamera() {
        if (!this.stream) return;
        
        try {
            // Stop current stream
            this.stream.getTracks().forEach(track => track.stop());
            
            // Get new stream with opposite facing mode
            const currentFacingMode = this.stream.getVideoTracks()[0].getSettings().facingMode || 'user';
            const newFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
            
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: newFacingMode
                },
                audio: false
            });
            
            this.videoEl.srcObject = this.stream;
            await this.waitForVideo();
            
            console.log(`📷 Switched to ${newFacingMode} camera`);
            return true;
        } catch (error) {
            console.error('Failed to switch camera:', error);
            return false;
        }
    }

    takeScreenshot() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        if (this.mode === 'photo' && this.photoEl) {
            // Screenshot from photo
            canvas.width = this.photoEl.naturalWidth || 800;
            canvas.height = this.photoEl.naturalHeight || 600;
            ctx.drawImage(this.photoEl, 0, 0, canvas.width, canvas.height);
        } else if (this.mode === 'camera' && this.videoEl) {
            // Screenshot from video
            canvas.width = this.videoEl.videoWidth || 640;
            canvas.height = this.videoEl.videoHeight || 480;
            ctx.drawImage(this.videoEl, 0, 0, canvas.width, canvas.height);
        }
        
        // Add overlay if present
        if (this.overlayEl && this.overlayEl.complete) {
            const scale = canvas.width / this.canvasEl.parentElement.clientWidth;
            const x = this.overlay.x * scale;
            const y = this.overlay.y * scale;
            const width = this.overlay.width * this.overlay.scale * scale;
            const height = this.overlay.height * this.overlay.scale * scale;
            
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(this.overlay.rotation * Math.PI / 180);
            ctx.drawImage(this.overlayEl, -width/2, -height/2, width, height);
            ctx.restore();
        }
        
        return canvas.toDataURL('image/png');
    }

    stopTryOn() {
        this.isActive = false;
        
        // Stop camera
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        // Clear video
        if (this.videoEl) {
            this.videoEl.srcObject = null;
        }
        
        // Hide overlay
        if (this.overlayEl) {
            this.overlayEl.classList.add('hidden');
        }
        
        // Detach interactions
        this.detachInteractions();
        
        console.log('🛑 Try-on stopped');
    }

    waitForVideo() {
        return new Promise((resolve) => {
            if (this.videoEl.readyState >= 2) {
                resolve();
            } else {
                this.videoEl.onloadeddata = resolve;
            }
        });
    }

    cleanup() {
        this.stopTryOn();
        if (this.overlayEl) {
            this.overlayEl.remove();
            this.overlayEl = null;
        }
    }
}

// Export globally
window.VirtualTryOn = VirtualTryOn;
