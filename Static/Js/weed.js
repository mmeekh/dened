const characterImage = new Image();
characterImage.src = 'Static/Assets/flappy-character.png';

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;  // Width of image
        this.height = 40; // Height of image
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        
        // Image setup
        this.image = characterImage;
        
        // Debug loading status to console
        this.image.onload = () => {
            console.log("Character image loaded successfully!");
        };
        
        this.image.onerror = () => {
            console.error("Failed to load character image from:", this.image.src);
        };
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
        ctx.save(); // Save current state
        
        // Calculate angle based on velocity for rotation
        let angle = 0;
        if (this.velocity < 0) {
            // Tilt up when moving up
            angle = -Math.PI/15; // About -12 degrees
        } else if (this.velocity > 1) {
            angle = Math.PI/15; // About 12 degrees
        }
        
        ctx.translate(this.x, this.y);
        ctx.rotate(angle);
        
        // First try to draw the image
        if (this.image.complete && this.image.naturalHeight !== 0) {
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
        } else {
            // Fallback: Draw a basic weed if image fails to load
            // This is just in case the image doesn't load
            ctx.fillStyle = '#44A244';
            ctx.beginPath();
            ctx.ellipse(0, 0, this.width/2, this.height/2, 0, 0, Math.PI * 2);
            ctx.fill();
            
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
        }
        
        ctx.restore(); // Restore state
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