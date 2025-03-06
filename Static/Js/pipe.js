class Pipe {
    constructor(canvas, x) {
        this.canvas = canvas;
        this.x = x;
        this.width = 70;
        this.gap = 240;  // Increased gap between pipes
        this.passed = false;
        
        // Random height for top pipe between 40 and canvas height - gap - 40
        this.topHeight = Math.floor(Math.random() * (canvas.height - this.gap - 80)) + 40;
        
        // Bottom pipe starts after the gap
        this.bottomY = this.topHeight + this.gap;
        this.bottomHeight = canvas.height - this.bottomY;
    }
    
    update(speed) {
        this.x -= speed;
    }
    
    isOffScreen() {
        return this.x + this.width < 0;
    }
    
    draw(ctx) {
        // Draw top pipe
        this.drawPipe(ctx, this.x, 0, this.width, this.topHeight, false);
        
        // Draw bottom pipe
        this.drawPipe(ctx, this.x, this.bottomY, this.width, this.bottomHeight, true);
    }
    
    drawPipe(ctx, x, y, width, height, isBottom) {
        // Main pipe body color - weed theme
        ctx.fillStyle = '#689F38';  // Green shade
        ctx.fillRect(x, y, width, height);
        
        // Pipe cap
        ctx.fillStyle = '#558B2F';  // Darker green for the cap
        
        if (isBottom) {
            // Bottom pipe cap is at the top of the pipe
            ctx.fillRect(x - 5, y, width + 10, 20);
        } else {
            // Top pipe cap is at the bottom of the pipe
            ctx.fillRect(x - 5, y + height - 20, width + 10, 20);
        }
        
        // Add some pipe details - vertical gradient for depth
        const gradient = ctx.createLinearGradient(x, y, x + width, y);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.1)');
        gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0.1)');
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, width, height);
        
        // Add small 'leaf' details to the pipe - weed theme
        ctx.fillStyle = '#7CB342';  // Lighter green
        
        const leafCount = Math.floor(height / 40);
        for (let i = 0; i < leafCount; i++) {
            const leafY = y + (isBottom ? i * 40 + 25 : height - i * 40 - 25);
            if (leafY > y && leafY < y + height - 10) {
                ctx.beginPath();
                ctx.ellipse(x + width/2, leafY, width/4, 10, 0, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
    
    checkCollision(weed) {
        // Get weed hitbox (slightly smaller than visual size for better gameplay)
        const hitboxReduction = 5;
        const weedLeft = weed.x - weed.width/2 + hitboxReduction;
        const weedRight = weed.x + weed.width/2 - hitboxReduction;
        const weedTop = weed.y - weed.height/2 + hitboxReduction;
        const weedBottom = weed.y + weed.height/2 - hitboxReduction;
        
        // Check collision with top pipe
        if (
            weedRight > this.x && 
            weedLeft < this.x + this.width && 
            weedTop < this.topHeight
        ) {
            return true;
        }
        
        // Check collision with bottom pipe
        if (
            weedRight > this.x && 
            weedLeft < this.x + this.width && 
            weedBottom > this.bottomY
        ) {
            return true;
        }
        
        return false;
    }
}