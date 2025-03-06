class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;  // Fixed horizontal position
        this.y = canvas.height / 2;  // Starting vertical position
        this.width = 40;
        this.height = 30;
        this.velocity = 0;
        this.gravity = 0.15;  // Reduced gravity for slower falling
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        this.rotation = 0;  // Current rotation angle in radians
    }
    
    update() {
        // Apply gravity
        this.velocity += this.gravity;
        
        // Limit fall speed
        if (this.velocity > 3.5) {
            this.velocity = 3.5;
        }
        
        // Add slight floating effect
        this.floatOffset += this.floatSpeed;
        let floatEffect = Math.sin(this.floatOffset) * 0.3;
        
        // Update position
        this.y += this.velocity + floatEffect;
        
        // Update rotation based on velocity
        this.rotation = this.velocity * 0.1;
        if (this.rotation > 0.5) this.rotation = 0.5;
        if (this.rotation < -0.3) this.rotation = -0.3;
        
        // Boundary checks to prevent going off-screen
        if (this.y - this.height/2 < 0) {
            this.y = this.height/2;
            this.velocity = 0;
        }
        
        // Check if hit the ground
        if (this.y + this.height/2 > this.canvas.height - 20) {
            this.y = this.canvas.height - 20 - this.height/2;
            this.velocity = 0;
            return true;  // Return true if hit the ground
        }
        
        return false;  // Return false if still flying
    }
    
    draw(ctx) {
        ctx.save();  // Save the current context state
        
        // Translate to character position and rotate
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rotation);
        
        // Draw main leaf body
        ctx.fillStyle = '#44A244';  // Dark green
        ctx.beginPath();
        ctx.ellipse(0, 0, this.width/2, this.height/2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw leaf veins
        ctx.strokeStyle = '#2E7D32';  // Darker green
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-this.width/3, 0);
        ctx.lineTo(this.width/3, 0);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, -this.height/3);
        ctx.lineTo(0, this.height/3);
        ctx.stroke();
        
        // Draw leaf details
        ctx.fillStyle = '#388E3C';  // Medium green
        
        // Left leaf segment
        ctx.beginPath();
        ctx.moveTo(-this.width/2, 0);
        ctx.lineTo(-this.width/4, -this.height/4);
        ctx.lineTo(0, 0);
        ctx.fill();
        
        // Right leaf segment
        ctx.beginPath();
        ctx.moveTo(this.width/2, 0);
        ctx.lineTo(this.width/4, -this.height/4);
        ctx.lineTo(0, 0);
        ctx.fill();
        
        // Bottom leaf segment
        ctx.beginPath();
        ctx.moveTo(-this.width/3, this.height/3);
        ctx.lineTo(0, this.height/2);
        ctx.lineTo(this.width/3, this.height/3);
        ctx.fill();
        
        // Add some highlights
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.beginPath();
        ctx.ellipse(-this.width/4, -this.height/4, this.width/8, this.height/8, 0, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.restore();  // Restore the context state
    }
    
    jump() {
        this.velocity = -6.0;  // Stronger jump force
        // Play jump sound
        game.sound.play('jump');
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;  // Slight upward momentum at start
        this.floatOffset = 0;
        this.rotation = 0;
    }
}