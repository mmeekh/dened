// Character image using your Imgur image
const characterImage = new Image();
// Direct link to your Imgur image
characterImage.src = 'https://imgur.com/a/Utkhunb';

// Debug logs to verify image loading
console.log("Character image loading from Imgur...");
characterImage.onload = function() {
    console.log("✅ Character image loaded successfully from Imgur!");
};
characterImage.onerror = function() {
    console.error("❌ Character image failed to load from Imgur");
    // Fallback to a simpler URL in case of error
    console.log("Trying fallback image URL...");
    this.src = 'https://imgur.com/a/Utkhunb';
};

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;  // Image width
        this.height = 40; // Image height
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        // Use the preloaded image
        this.image = characterImage;
    }
    
    update() {
        this.velocity += this.gravity;
        if (this.velocity > 2.0) {
            this.velocity = 2.0;
        }
        
        this.floatOffset += this.floatSpeed;
        let floatEffect = Math.sin(this.floatOffset) * 0.3;
        this.y += this.velocity + floatEffect;
        
        if (this.y - this.height/2 < 0) {
            this.y = this.height/2;
            this.velocity = 0;
        }
        
        if (this.y + this.height/2 > this.canvas.height - 20) {
            this.y = this.canvas.height - 20 - this.height/2;
            this.velocity = 0;
            return true;
        }
        return false;
    }
    
    draw(ctx) {
        ctx.save(); // Save current drawing state
        
        // Calculate angle for character movement
        let angle = 0;
        if (this.velocity < 0) {
            // Tilt slightly up when moving upward
            angle = -Math.PI/15; // About -12 degrees
        } else if (this.velocity > 1) {
            angle = Math.PI/15; // About 12 degrees
        }
        
        // Move to character position and apply rotation
        ctx.translate(this.x, this.y);
        ctx.rotate(angle);
        
        // Draw the character image with proper checking
        if (this.image.complete && this.image.naturalHeight !== 0) {
            // If image is loaded successfully, draw it
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
        } else {
            // Fallback drawing if image fails to load
            this.drawFallbackCharacter(ctx);
        }
        
        ctx.restore(); // Restore drawing state
    }
    
    // Fallback drawing method with more details
    drawFallbackCharacter(ctx) {
        // Main leaf shape (green circle)
        ctx.fillStyle = '#44A244';
        ctx.beginPath();
        ctx.ellipse(0, 0, this.width/2, this.height/2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Leaf cross pattern
        ctx.strokeStyle = '#2E7D32';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-this.width/3, 0);
        ctx.lineTo(this.width/3, 0);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, -this.height/3);
        ctx.lineTo(0, this.height/3);
        ctx.stroke();
        
        // Add some leaf details
        ctx.fillStyle = '#388E3C';
        ctx.beginPath();
        ctx.moveTo(-this.width/2, 0);
        ctx.lineTo(-this.width/4, -this.height/4);
        ctx.lineTo(0, 0);
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(this.width/2, 0);
        ctx.lineTo(this.width/4, -this.height/4);
        ctx.lineTo(0, 0);
        ctx.fill();
    }
    
    jump() {
        this.velocity = -3.8;
        game.sound.play('jump');
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}